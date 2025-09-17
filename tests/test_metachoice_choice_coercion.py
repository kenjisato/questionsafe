from __future__ import annotations

import pytest

from questionsafe.meta import MetaChoice, Stem


def test_set_choices_dict_and_generate():
    mc = MetaChoice()
    mc.set_choices({
        "A": "Alpha long",
        "B": "Bravo long",
        "C": "Charlie long",
    })
    stem = Stem("K1", "Pick A and one more").set_choices_correct({"A"})
    mc.add_stem(stem)
    group = mc.generate_multichoice(n=2, limit=1, seed=1)
    assert len(group.variants) == 1
    q = group.variants[0]
    q.validate()
    pos = [a for a in q.answers if a.fraction > 0]
    assert len(pos) == 1
    assert pos[0].text == "Alpha long"


def test_set_choices_shorthand_strings():
    mc = MetaChoice()
    mc.set_choices(["A: Alpha", "B"])  # B -> key==text
    mc.add_stem(Stem("K2", "Pick B").set_choices_correct({"B"}))
    group = mc.generate_multichoice(n=1, limit=1, seed=2)
    q = group.variants[0]
    q.validate()
    pos = [a for a in q.answers if a.fraction > 0]
    assert pos[0].text == "B"


def test_set_choices_duplicate_raises():
    mc = MetaChoice()
    with pytest.raises(ValueError):
        mc.set_choices(["A: one", "A: two"])  # duplicate key A


def test_add_choice_duplicate_raises():
    mc = MetaChoice().set_choices({"A": "one"})
    with pytest.raises(ValueError):
        mc.add_choice("A: two")

