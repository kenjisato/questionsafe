# Constrained choice sampling utilities
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Generator, Hashable, Iterable, Iterator, List, Optional, Sequence, Set, Tuple
import random


@dataclass(frozen=True)
class Constraint:
    """A constraint over a set of items.

    - id: logical identifier (for diagnostics only)
    - members: the subset of items this constraint applies to
    - min: minimum number of selected items that must come from members
    - max: maximum number of selected items that may come from members
            None => no cap (interpreted as total), negative => relative to
            total, e.g., -1 means at most total-1
    """

    id: str
    members: frozenset[Hashable]
    min: int = 0
    max: Optional[int] = None
    description: Optional[str] = None

    def __post_init__(self):
        # cast members to frozenset for hashability
        object.__setattr__(self, "members", frozenset(self.members))
        if self.min < 0:
            raise ValueError("Constraint.min must be >= 0")


def _suffix_counts(items: Sequence[Hashable], groups: Sequence[Constraint]) -> Dict[Constraint, List[int]]:
    suf = {g: [0] * (len(items) + 1) for g in groups}
    for g in groups:
        c = 0
        gm = g.members
        for i in range(len(items) - 1, -1, -1):
            if items[i] in gm:
                c += 1
            suf[g][i] = c
    return suf


def _normalize_bounds(groups: Sequence[Constraint], total: int) -> Dict[Constraint, Tuple[int, int]]:
    bounds: Dict[Constraint, Tuple[int, int]] = {}
    for g in groups:
        if g.max is None:
            bounds[g] = (g.min, total)
        else:
            U = g.max
            if U < 0:
                bounds[g] = (g.min, total + U)  # e.g., -1 => total-1
            else:
                bounds[g] = (g.min, U)
    return bounds


def constrained_subsets(
    items: Iterable[Hashable],
    groups: Iterable[Constraint],
    n: int,
    *,
    limit: Optional[int] = None,
    seed: Optional[int] = None,
    randomize_order: bool = True,
    randomize_branch: bool = True,
) -> Iterator[Set[Hashable]]:
    """Yield subsets of size n from items that satisfy all constraints.

    - items must contain hashable elements.
    - groups may overlap; all bounds are enforced simultaneously. You may supply
      multiple Constraint with the same `id` to represent combined constraints
      (e.g., global and local); they will both be enforced without merging.
    - Bounds semantics follow Constraint.
    - Enumeration order is randomized by default for diversity; set seed for
      reproducibility. Use limit to cap the number of yielded subsets.
    """
    items_list: List[Hashable] = list(items)
    if n < 0 or n > len(items_list):
        return iter(())

    groups_list: List[Constraint] = list(groups)

    # Integrity: every group's members must be from the item universe
    item_set = set(items_list)
    for g in groups_list:
        diff = g.members - item_set
        if diff:
            raise ValueError(f"Constraint {g.id} has members not present in items: {sorted(diff)}")

    rng = random.Random(seed)
    if randomize_order:
        items_work = items_list[:]
        rng.shuffle(items_work)
    else:
        items_work = items_list

    bounds = _normalize_bounds(groups_list, total=len(items_work))
    suf = _suffix_counts(items_work, groups_list)

    chosen: List[Hashable] = []
    count: Dict[Constraint, int] = {g: 0 for g in groups_list}
    emitted = 0

    def add(x: Hashable):
        chosen.append(x)
        for g in groups_list:
            if x in g.members:
                count[g] += 1

    def rem(x: Hashable):
        chosen.pop()
        for g in groups_list:
            if x in g.members:
                count[g] -= 1

    def violates_upper() -> bool:
        for g, (L, U) in bounds.items():
            if count[g] > U:
                return True
        return False

    def lower_reachable(i: int) -> bool:
        for g, (L, U) in bounds.items():
            if count[g] + suf[g][i] < L:
                return False
        return True

    def meets_all_bounds() -> bool:
        for g, (L, U) in bounds.items():
            c = count[g]
            if not (L <= c <= U):
                return False
        return True

    def dfs(i: int) -> Generator[Set[Hashable], None, None]:
        nonlocal emitted
        if limit is not None and emitted >= limit:
            return

        picked = len(chosen)
        rem_items = len(items_work) - i

        if picked == n:
            if meets_all_bounds():
                emitted += 1
                yield set(chosen)
            return

        if picked > n or picked + rem_items < n:
            return

        if violates_upper() or not lower_reachable(i):
            return

        if i == len(items_work):
            return

        x = items_work[i]

        include_first = True
        if randomize_branch:
            # If x helps any unmet lower bound, prefer including; else random flip
            helps = any((count[g] < bounds[g][0]) and (x in g.members) for g in groups_list)
            include_first = helps or (rng.random() < 0.5)

        if include_first:
            add(x)
            yield from dfs(i + 1)
            rem(x)
            yield from dfs(i + 1)
        else:
            yield from dfs(i + 1)
            add(x)
            yield from dfs(i + 1)
            rem(x)

    yield from dfs(0)

