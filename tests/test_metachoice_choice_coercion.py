from __future__ import annotations

import pytest

from questionsafe.meta import MetaChoice


def test_set_choices_dict_and_generate():
    mc = MetaChoice()
    mc.set_choices({"A": "Alpha long", "B": "Bravo long", "C": "Charlie long"})
    mc.add_stem("K1", "Pick A and one more", correct={"A"})
    group = mc.generate_multichoice(n=2, limit=1, seed=1)
    assert len(group.variants) == 1
    q = group.variants[0]
    q.validate()
    pos = [a for a in q.answers if a.fraction > 0]
    assert len(pos) == 1
    assert pos[0].text == "Alpha long"


def test_set_choices_shorthand_strings():
    mc = MetaChoice()
    mc.set_choices({"A": "Alpha", "B": "B"})
    mc.add_stem("K2", "Pick B", correct={"B"})
    group = mc.generate_multichoice(n=1, limit=1, seed=2)
    q = group.variants[0]
    q.validate()
    pos = [a for a in q.answers if a.fraction > 0]
    assert pos[0].text == "B"


def test_set_choices_empty_key_raises():
    mc = MetaChoice()
    with pytest.raises(ValueError):
        mc.set_choices({"": "x"})



