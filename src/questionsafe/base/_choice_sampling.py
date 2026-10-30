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
) -> Iterator[Set[Hashable]]:
    """Yield distinct subsets of size n from items that satisfy all constraints.

    - items must contain hashable elements.
    - groups may overlap; all bounds are enforced simultaneously. You may supply
      multiple Constraint with the same `id` to represent combined constraints
      (e.g., global and local); they will both be enforced without merging.
    - Bounds semantics follow Constraint.
    - Usage is spread: each subset is the first feasible, not yet yielded one when
      items are ranked by how often they have been yielded so far, so a small
      `limit` still cycles through the items. Ties are broken at random (seeded)
      if randomize_order, else by input order.
    - Use limit to cap the number of yielded subsets; None yields all of them.
    """
    items_list: List[Hashable] = list(items)
    if n < 0 or n > len(items_list):
        return

    groups_list: List[Constraint] = list(groups)

    # Integrity: every group's members must be from the item universe
    item_set = set(items_list)
    for g in groups_list:
        diff = g.members - item_set
        if diff:
            raise ValueError(f"Constraint {g.id} has members not present in items: {sorted(diff)}")

    rng = random.Random(seed)
    bounds = _normalize_bounds(groups_list, total=len(items_list))
    usage: Dict[Hashable, int] = {x: 0 for x in items_list}
    seen: Set[frozenset] = set()

    while limit is None or len(seen) < limit:
        tiebreak = {x: (rng.random() if randomize_order else i) for i, x in enumerate(items_list)}
        ranked = sorted(items_list, key=lambda x: (usage[x], tiebreak[x]))
        subset = next((s for s in _feasible_subsets(ranked, groups_list, bounds, n) if s not in seen), None)
        if subset is None:
            return
        seen.add(subset)
        for x in subset:
            usage[x] += 1
        yield set(subset)


def _feasible_subsets(
    items: Sequence[Hashable],
    groups: Sequence[Constraint],
    bounds: Dict[Constraint, Tuple[int, int]],
    n: int,
) -> Iterator[frozenset]:
    """Yield every feasible subset, preferring earlier items (depth-first, include first)."""
    suf = _suffix_counts(items, groups)
    chosen: List[Hashable] = []
    count: Dict[Constraint, int] = {g: 0 for g in groups}

    def step(x: Hashable, d: int) -> None:
        for g in groups:
            if x in g.members:
                count[g] += d

    def dfs(i: int) -> Generator[frozenset, None, None]:
        if len(chosen) == n:
            if all(L <= count[g] <= U for g, (L, U) in bounds.items()):
                yield frozenset(chosen)
            return
        if len(chosen) + len(items) - i < n:
            return
        if any(count[g] > U or count[g] + suf[g][i] < L for g, (L, U) in bounds.items()):
            return
        x = items[i]
        chosen.append(x)
        step(x, 1)
        yield from dfs(i + 1)
        step(x, -1)
        chosen.pop()
        yield from dfs(i + 1)

    yield from dfs(0)
