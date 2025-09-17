from __future__ import annotations

from questionsafe.meta import MetaChoice, Stem, Constraint


def test_metachoice_generates_valid_multichoice_single_correct():
    pool = ["T1", "T2", "P1", "P2", "A1"]
    mc = MetaChoice()
    mc.set_choices(pool)

    # Global constraints
    mc.add_constraint(Constraint("term", choices={"T1", "T2"}, min=1, max=1))  # exactly one term
    mc.add_constraint(Constraint("policy", choices={"P1", "P2"}, min=0, max=1))  # at most one policy

    # Stem requires 3 choices; mark correct choices directly (terms)
    mc.add_stem(Stem("TERM_Q", "Who served two terms?").set_choices_correct({"T1", "T2"}))

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
    mc = MetaChoice().set_choices(pool)

    mc.add_constraint(Constraint("term", choices={"T1", "T2"}, min=1, max=1))
    mc.add_constraint(Constraint("policy", choices={"P1", "P2"}, min=0, max=1))

    # Local: require at least one policy in addition to one term
    stem = Stem("TERM_POLICY_Q", "Pick a term and a policy").set_choices_correct({"T1", "T2"})
    stem.add_constraint(Constraint("policy", choices={"P1", "P2"}, min=1, max=1))
    mc.add_stem(stem)

    group = mc.generate_multichoice(n=3, seed=123, limit=1)
    q = group.variants[0]
    q.validate()
    texts = [a.text for a in q.answers]
    assert any(t in {"P1", "P2"} for t in texts)  # at least one policy present
    assert any(t in {"T1", "T2"} for t in texts)  # at least one term present
