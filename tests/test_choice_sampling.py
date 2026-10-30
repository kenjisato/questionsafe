from __future__ import annotations

from collections import Counter

from questionsafe.base._choice_sampling import Constraint, constrained_subsets


def test_constrained_subsets_basic_union_constraints():
    items = ["A", "B", "C", "D"]
    # Global: require at least 1 from {A,B}
    g1 = Constraint(id="ab", members={"A", "B"}, min=1)
    # Global: at most 1 from {C,D}
    g2 = Constraint(id="cd", members={"C", "D"}, min=0, max=1)
    # Local: tighten {A,B} to at most 1 as well (so exactly 1 from A/B)
    l1 = Constraint(id="ab", members={"A", "B"}, min=0, max=1)

    subsets = list(constrained_subsets(items, [g1, g2, l1], n=2, limit=100, seed=42))
    assert subsets, "Should find at least one feasible subset"
    for s in subsets:
        assert len(s) == 2
        ab = len(s & {"A", "B"})
        cd = len(s & {"C", "D"})
        assert ab == 1  # due to union of (min>=1, max<=1)
        assert cd <= 1


def test_constrained_subsets_no_solution_yields_empty():
    items = ["A", "B"]
    # Impossible: need 2 from {A,B} but we will pick n=1
    g = Constraint(id="ab", members={"A", "B"}, min=2)
    subsets = list(constrained_subsets(items, [g], n=1, limit=10, seed=1))
    assert subsets == []



def test_constrained_subsets_spreads_usage_when_limit_is_small():
    correct = [f"C{i}" for i in range(6)]
    wrong = [f"W{i}" for i in range(7)]
    one_correct = Constraint(id="correct", members=frozenset(correct), min=1, max=1)

    subsets = list(constrained_subsets(correct + wrong, [one_correct], n=4, limit=7, seed=0))

    assert len(subsets) == len({frozenset(s) for s in subsets}) == 7
    usage = Counter(x for s in subsets for x in s)
    # 7 corrects over 6 choices, 21 distractors over 7 choices
    assert sorted(usage[c] for c in correct) == [1, 1, 1, 1, 1, 2]
    assert all(usage[w] == 3 for w in wrong)


def test_constrained_subsets_is_deterministic_for_a_seed():
    items = [f"X{i}" for i in range(8)]

    def run(seed):
        return list(constrained_subsets(items, [], n=3, limit=5, seed=seed))

    assert run(3) == run(3)


def test_constrained_subsets_without_limit_yields_every_subset_once():
    items = ["A", "B", "C", "D", "E"]
    subsets = list(constrained_subsets(items, [], n=2, seed=1))
    assert len(subsets) == len({frozenset(s) for s in subsets}) == 10
