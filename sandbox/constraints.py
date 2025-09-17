from typing import Dict, Set, List, Tuple, Optional, Generator

def _suffix_counts(items: List[str], groups: Dict[str, Set[str]]) -> Dict[str, List[int]]:
    """suffix[g][i] = # of items in items[i:] that belong to group g."""
    suf = {g: [0]*(len(items)+1) for g in groups}
    for g, S in groups.items():
        c = 0
        for i in range(len(items)-1, -1, -1):
            if items[i] in S:
                c += 1
            suf[g][i] = c
    return suf

def enumerate_sets(
    choices: List[str],
    groups: Dict[str, Set[str]],              # includes 'correct', pair-bans as groups, etc.
    bounds: Dict[str, Tuple[int, int]],       # (L_k, U_k) for each group
    N: int,
    limit: Optional[int] = None,
) -> Generator[Set[str], None, None]:
    """Yield sets S ⊆ choices with |S| = N and L_k ≤ |S∩G_k| ≤ U_k for all groups."""
    items = list(choices)
    for g in groups:                           # default any missing bounds
        bounds.setdefault(g, (0, N))
    suf = _suffix_counts(items, groups)

    chosen: List[str] = []
    count: Dict[str, int] = {g: 0 for g in groups}
    out = 0

    def add(x: str):
        chosen.append(x)
        for g, S in groups.items():
            if x in S:
                count[g] += 1

    def rem(x: str):
        chosen.pop()
        for g, S in groups.items():
            if x in S:
                count[g] -= 1

    def violates_upper() -> bool:
        for g, (_L, U) in bounds.items():
            if count[g] > U:
                return True
        return False

    def lower_reachable(i: int) -> bool:
        # Even taking ALL remaining eligible items, can we still hit each lower bound?
        for g, (L, _U) in bounds.items():
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
        if limit is not None and out >= limit:
            return
        picked = len(chosen)
        rem_items = len(items) - i

        # EARLY leaf: if we've already picked N, we must skip the rest
        if picked == N:
            if meets_all_bounds():
                out += 1
                yield set(chosen)
            return

        # Cardinality pruning
        if picked > N or picked + rem_items < N:
            return

        # Group pruning
        if violates_upper():
            return
        if not lower_reachable(i):
            return

        if i == len(items):                    # FINAL leaf (covers N==len(items) cases)
            return

        x = items[i]

        # include x
        add(x)
        yield from dfs(i + 1)
        rem(x)

        # skip x
        yield from dfs(i + 1)

    yield from dfs(0)

def find_one(
    choices: List[str],
    groups: Dict[str, Set[str]],
    bounds: Dict[str, Tuple[int, int]],
    N: int,
) -> Optional[Set[str]]:
    return next(enumerate_sets(choices, groups, bounds, N, limit=1), None)



#------
# The following sandbox examples reference Choice/ChoiceGroup symbols that are not
# defined in this file. Commenting them out to satisfy linters while keeping context.
# c1 = Choice("He served one period.")
# c2 = Choice("He served two periods.")
# c3 = Choice("He withdrew from the TPP.")
# c4 = Choice("He was awarded the Nobel Peace Prize.")
# c5 = Choice("He led the post-pandemic recovery.")
# c6 = Choice("He is/was a Democrat.")
# correct = ChoiceGroup("correct", {c2, c4, c6}, (1, -1))
# terms = ChoiceGroup("terms", {c1, c2}, (1, 1))
# policy = ChoiceGroup("policy", {c3, c5}, (1, 0))
# award = ChoiceGroup("award", {c4}, (0, 0))
# party = ChoiceGroup("party", {c6}, (0, None))


class ChoiceRange:
    pass 





#--------

# Universe
choices = ["C1","C2","C3","C4","C5","C6"]

# Obama stem: correct vs wrong for THIS stem
correct = {"C2","C4","C6"}                 # two terms, Nobel Peace Prize, Democrat
wrong   = set(choices) - correct

# Groups (overlaps are fine)
groups = {
    "correct": correct,                    # correctness constraint
    "terms": {"C1","C2"},                  # tenure-count statements
    "policy": {"C3","C5"},
    "award": {"C4"},
    "party": {"C6"},
    # Pair ban example (as a group): cannot show both C3 and C5 together
    "no_both_policy": {"C3","C5"},
}

N = 4 # total options in the item

# Bounds (anything not listed defaults to (0, N))
bounds = {
    "correct": (1, N-1),     # multi-response requires at least one correct
    "terms":   (1, 1),     # exactly one of {C1, C2} appears (not both, not zero)
    "policy":  (1, N),     # show at least one policy item
    "no_both_policy": (0, 1),  # at most one of {C3, C5}  (turns "at least one" into "exactly one")
}

# Find one feasible set
one = find_one(choices, groups, bounds, N)
print("One feasible set:", one)

# Enumerate up to 3 different sets (different combinations that satisfy bounds)
for i, S in enumerate(enumerate_sets(choices, groups, bounds, N, limit=5), 1):
    print(f"{i}: {sorted(S)}")
