from dataclasses import dataclass
from typing import Dict, Set, List, Tuple, Optional, Generator
import random

@dataclass(frozen=True)
class Choice:
    text: str
    def __key(self): return self.text
    def __hash__(self): return hash(self.__key())
    def __eq__(self, other):
        if not isinstance(other, Choice): return NotImplemented
        return self.__key() == other.__key__()

@dataclass(frozen=True)
class ChoiceGroup:
    id: str
    members: Set[Choice]
    bounds: Optional[Tuple[int, Optional[int]]] = None
    description: Optional[str] = None
    def __key(self):
        members = tuple(sorted(self.members, key=lambda x: x.text))
        return (self.id, members, self.bounds)
    def __hash__(self): return hash(self.__key())
    def __eq__(self, other):
        if not isinstance(other, ChoiceGroup): return NotImplemented
        return self.__key() == other.__key__()

@dataclass
class ChoiceGenerator:
    choices: List[Choice]
    groups: List[ChoiceGroup]
    n: int = 4
    limit: Optional[int] = None
    seed: Optional[int] = None
    randomize_order: bool = True
    randomize_branch: bool = True

    def __post_init__(self):
        choice_set = set(self.choices)
        for g in self.groups:
            diff = g.members - choice_set
            if diff:
                raise ValueError(f"Group {g.id} has members not in choices: {[c.text for c in diff]}")

    # NOTE: compute suffix counts on the SAME 'items' order you will search
    def _suffix_counts(self, items: List[Choice]) -> Dict[ChoiceGroup, List[int]]:
        suf = {g: [0]*(len(items)+1) for g in self.groups}
        for g in self.groups:
            c = 0
            for i in range(len(items)-1, -1, -1):
                if items[i] in g.members:
                    c += 1
                suf[g][i] = c
        return suf

    def _find_feasible_choices(self) -> Generator[Set[Choice], None, None]:
        rng = random.Random(self.seed)

        items = list(self.choices)
        if self.randomize_order:
            rng.shuffle(items)  # randomized traversal order

        # Normalize group bounds based on |choices|
        bounds: Dict[ChoiceGroup, Tuple[int, int]] = {}
        total = len(items)
        for g in self.groups:
            if g.bounds is None:
                bounds[g] = (0, total)
            else:
                L, U = g.bounds
                if U is None:
                    bounds[g] = (L, total)
                elif U < 0:
                    bounds[g] = (L, total + U)  # e.g., U=-1 means at most total-1
                else:
                    bounds[g] = (L, U)

        suf = self._suffix_counts(items)

        chosen: List[Choice] = []
        count: Dict[ChoiceGroup, int] = {g: 0 for g in self.groups}
        out = 0

        def add(x: Choice):
            chosen.append(x)
            for g in self.groups:
                if x in g.members:
                    count[g] += 1

        def rem(x: Choice):
            chosen.pop()
            for g in self.groups:
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

        def dfs(i: int):
            nonlocal out
            if self.limit is not None and out >= self.limit:
                return

            picked = len(chosen)
            rem_items = len(items) - i

            # early leaf: exactly n picked
            if picked == self.n:
                if meets_all_bounds():
                    out += 1
                    yield set(chosen)
                return

            # cardinality pruning
            if picked > self.n or picked + rem_items < self.n:
                return

            # group pruning
            if violates_upper() or not lower_reachable(i):
                return

            if i == len(items):
                return

            x = items[i]

            # Decide branch order randomly (but nudge towards satisfying lower bounds)
            include_first = True
            if self.randomize_branch:
                # If x helps any unmet lower bound, prefer including; else random coin flip
                helps = any((count[g] < bounds[g][0]) and (x in g.members) for g in self.groups)
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

    def __iter__(self):
        self._it = self._find_feasible_choices()
        return self

    def __next__(self):
        return next(self._it)


# ---------- Example ----------

choices = [
    Choice("He served one period."),
    Choice("He served two periods."),
    Choice("He withdrew from the TPP."),
    Choice("He was awarded the Nobel Peace Prize."),
    Choice("He led the post-pandemic recovery."),
    Choice("He is/was a Democrat.")
]

gen = ChoiceGenerator(
    choices=choices,
    groups=[
        ChoiceGroup("correct", {choices[1], choices[3], choices[5]}, (1, -1)),
        ChoiceGroup("terms", {choices[0], choices[1]}, (1, 1)),
        ChoiceGroup("policy", {choices[2], choices[4]}, (0, None)),
        ChoiceGroup("award", {choices[3]}, (0, None)),
        ChoiceGroup("party", {choices[5]}, None),
        # Example: not both policy picks — group bound (0,1)
        ChoiceGroup("no_both_policy", {choices[2], choices[4]}, (0, 1)),
    ],
    n=3,
    limit=10,
    #seed=2025,                 # reproducible randomness
    randomize_order=True,      # shuffle order of items
    randomize_branch=True      # randomize include-vs-skip first
)

for s in gen:
    print(sorted(c.text for c in s))
