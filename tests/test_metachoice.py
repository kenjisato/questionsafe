from __future__ import annotations

from questionsafe.meta import MetaChoice, Constraint


def test_metachoice_generates_valid_multichoice_single_correct():
    pool = ["T1", "T2", "P1", "P2", "A1"]
    mc = MetaChoice()
    mc.set_choices({k: k for k in pool})

    # Global constraints
    mc.set_constraints({
        "term": Constraint("T1", "T2", min=1, max=1, id="term"),  # exactly one term
        "policy": Constraint("P1", "P2", min=0, max=1, id="policy"),  # at most one policy
    })

    # Stem requires 3 choices; mark correct choices directly (terms)
    mc.add_stem("TERM_Q", "Who served two terms?", correct={"T1", "T2"})

    group = mc.generate_multichoice(n=3)
    assert len(group.variants) == 1
    q = group.variants[0]
    # Validate shape
    q.validate()
    assert len(q.answers) == 3
    # Exactly one correct with 100
    positives = [a for a in q.answers if a.fraction > 0]
    assert len(positives) == 1 and abs(float(positives[0].fraction) - 100.0) < 1e-6


def test_metachoice_with_local_constraint_union():
    pool = ["T1", "T2", "P1", "P2", "A1"]
    mc = MetaChoice().set_choices({k: k for k in pool})

    mc.set_constraints({
        "term": Constraint("T1", "T2", min=1, max=1, id="term"),
        "policy": Constraint("P1", "P2", min=0, max=1, id="policy"),
    })

    # Local: require at least one policy in addition to one term
    mc.add_stem(
        "TERM_POLICY_Q",
        "Pick a term and a policy",
        correct={"T1", "T2"},
        constraints={"policy": Constraint("P1", "P2", min=1, max=1, id="policy")},
    )

    group = mc.generate_multichoice(n=3, seed=123, limit=1)
    q = group.variants[0]
    q.validate()
    texts = [a.text for a in q.answers]
    assert any(t in {"P1", "P2"} for t in texts)  # at least one policy present
    assert any(t in {"T1", "T2"} for t in texts)  # at least one term present


def _pool_six_correct_seven_wrong():
    correct = [f"C{i}" for i in range(6)]
    wrong = [f"W{i}" for i in range(7)]
    mc = MetaChoice().set_choices({k: k for k in correct + wrong})
    mc.add_stem("S", "Which is correct?", correct=correct)
    return mc, correct


def test_generate_singlechoice_spreads_variants_over_correct_choices():
    mc, correct = _pool_six_correct_seven_wrong()
    group = mc.generate_singlechoice(n=4, limit=7, seed=1)
    chosen = [next(str(a.text) for a in q.answers if a.fraction == 100) for q in group]
    assert set(chosen) == set(correct)


def test_generate_multichoice_spreads_variants_over_correct_choices():
    mc, correct = _pool_six_correct_seven_wrong()
    group = mc.generate_multichoice(n=4, limit=6, seed=1, nc=1)
    chosen = [next(str(a.text) for a in q.answers if a.fraction > 0) for q in group]
    assert sorted(chosen) == correct
