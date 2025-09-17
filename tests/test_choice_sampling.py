from __future__ import annotations

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

