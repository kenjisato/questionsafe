from __future__ import annotations

from questionsafe.meta import MetaChoice, Stem, Constraint
from questionsafe.questions.multichoice import MultiChoice


def test_multichoice_with_prototype_defaults():
    mc = MetaChoice().set_choices({
        "A": "Alpha",
        "B": "Bravo",
        "C": "Charlie",
    })
    mc.add_stem(Stem("S1", "Pick B").set_choices_correct({"B"}))

    proto = MultiChoice(name="TEMPLATE").set_choice_layout(labels="abc", shuffle=False)
    grp = mc.generate_multichoice(n=2, limit=1, seed=1, prototype=proto)

    q = grp.variants[0]
    assert q.labels == "abc"
    assert q.shuffle is False


def test_singlechoice_with_prototype_defaults():
    mc = MetaChoice().set_choices(["A", "B", "C"])  # key==text shorthand
    mc.add_stem(Stem("S2", "Pick A").set_choices_correct({"A"}))

    from questionsafe.questions.singlechoice import SingleChoice

    proto = SingleChoice(name="TEMPLATE").set_choice_layout(labels="123", shuffle=False)
    grp = mc.generate_singlechoice(n=2, limit=1, seed=2, prototype=proto)

    q = grp.variants[0]
    assert q.labels == "123"
    assert q.shuffle is False

