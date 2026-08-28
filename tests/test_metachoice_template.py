from __future__ import annotations

import pytest

from questionsafe import Text
from questionsafe.meta import MetaChoice, Constraint


def _basic_mc(**kwargs) -> MetaChoice:
    """Pool of one correct and three distractors, one stem."""
    mc = MetaChoice(**kwargs)
    mc.set_choices({"C1": "Correct 1", "D1": "Wrong 1", "D2": "Wrong 2", "A1": "Attractor"})
    return mc


def test_stem_text_preserves_markdown_format():
    mc = _basic_mc()
    mc.add_stem("Q1", Text("Which is *correct*?", format="markdown"), correct=["C1"])
    group = mc.generate_multichoice(n=3, seed=1)
    q = group.variants[0]
    assert q.questiontext.format == "markdown"
    assert q.questiontext.text == "Which is *correct*?"


def test_add_stem_exclude_never_samples_excluded():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=["C1"], exclude=["A1"])
    mc.add_stem("Q2", "Pick another", correct=["C1"])
    group = mc.generate_multichoice(n=3, limit=10, seed=42)
    q1_texts = {a.text for q in group.variants if q.name.endswith("Q1") for a in q.answers}
    q2_texts = {a.text for q in group.variants if q.name.endswith("Q2") for a in q.answers}
    assert "Attractor" not in q1_texts
    # With n=3 out of a 4-item pool and 10 subsets allowed, Q2 must hit A1 somewhere.
    assert "Attractor" in q2_texts


def test_exclude_overlapping_correct_raises():
    mc = _basic_mc()
    with pytest.raises(ValueError, match="C1"):
        mc.add_stem("Q1", "Pick one", correct=["C1"], exclude=["C1"])


def test_set_choices_correct_after_exclude_raises():
    from questionsafe.meta import Stem

    stem = Stem(key="Q1", text="Pick one")
    stem.set_choices_excluded(["A1"])
    with pytest.raises(ValueError, match="A1"):
        stem.set_choices_correct(["A1"])


def test_excluded_id_reserved_for_global_constraints():
    mc = _basic_mc()
    with pytest.raises(ValueError, match="__excluded__"):
        mc.add_constraint("A1", min=0, max=0, id="__excluded__")


def test_excluded_id_reserved_for_stem_constraints():
    from questionsafe.meta import Stem

    stem = Stem(key="Q1", text="Pick one")
    with pytest.raises(ValueError, match="set_choices_excluded"):
        stem.add_constraint(Constraint("A1", min=0, max=0, id="__excluded__"))


def test_add_stem_duplicate_key_raises():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=["C1"])
    with pytest.raises(ValueError, match="Q1"):
        mc.add_stem("Q1", "Pick again", correct=["C1"])


def test_validate_passes_and_returns_self():
    mc = _basic_mc()
    mc.set_constraints({"attractor": Constraint("A1", max=1)})
    mc.add_stem("Q1", "Pick one", correct=["C1"], exclude=["A1"])
    assert mc.validate() is mc


def test_validate_empty_pool():
    mc = MetaChoice()
    mc.add_stem("Q1", "Pick one", correct=["C1"])
    with pytest.raises(ValueError, match="pool is empty"):
        mc.validate()


def test_validate_no_stems():
    mc = _basic_mc()
    with pytest.raises(ValueError, match="[Nn]o stems"):
        mc.validate()


def test_validate_correct_key_not_in_pool():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=["NOPE"])
    with pytest.raises(ValueError, match="NOPE"):
        mc.validate()


def test_validate_excluded_key_not_in_pool():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=["C1"], exclude=["NOPE"])
    with pytest.raises(ValueError, match="NOPE"):
        mc.validate()


def test_validate_local_constraint_member_not_in_pool():
    mc = _basic_mc()
    mc.add_stem(
        "Q1",
        "Pick one",
        correct=["C1"],
        constraints={"bad": Constraint("NOPE", min=1)},
    )
    with pytest.raises(ValueError, match="NOPE"):
        mc.validate()


def test_validate_min_greater_than_max():
    mc = _basic_mc()
    mc.add_stem(
        "Q1",
        "Pick one",
        correct=["C1"],
        constraints={"bad": Constraint("D1", "D2", min=2, max=1)},
    )
    with pytest.raises(ValueError, match="bad"):
        mc.validate()


def test_validate_constraint_starved_by_exclusion():
    mc = _basic_mc()
    mc.set_constraints({"attractor": Constraint("A1", min=1)})
    mc.add_stem("Q1", "Pick one", correct=["C1"], exclude=["A1"])
    mc.add_stem("Q2", "Pick another", correct=["C1"])
    # Q1 excludes the only member of a min=1 constraint -> infeasible template
    with pytest.raises(ValueError, match="attractor"):
        mc.validate()


def test_validate_empty_correct_set():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=[])
    with pytest.raises(ValueError, match="Q1"):
        mc.validate()


def test_generate_snaps_uniform_correct_fractions():
    mc = _basic_mc()
    mc.set_choices({"C1": "a", "C2": "b", "C3": "c", "D1": "d"})
    mc.add_stem("Q1", "Pick", correct=["C1", "C2", "C3"])
    group = mc.generate_multichoice(n=4, seed=1)
    q = group.variants[0]
    fractions = sorted(float(a.fraction) for a in q.answers if float(a.fraction) > 0)
    assert fractions == [33.33333, 33.33333, 33.33333]


def test_name_prefixes_variant_names():
    mc = _basic_mc(name="Econ/Demo")
    mc.add_stem("Q1", "Pick one", correct=["C1"])
    group = mc.generate_multichoice(n=3, seed=1)
    assert group.variants[0].name == "Econ/Demo/Q1"


def test_default_variant_names_unchanged():
    mc = _basic_mc()
    mc.add_stem("Q1", "Pick one", correct=["C1"])
    group = mc.generate_multichoice(n=3, seed=1)
    assert group.variants[0].name == "Q1"


def test_source_propagates_to_group():
    mc = _basic_mc(source="bank/metachoice.md")
    mc.add_stem("Q1", "Pick one", correct=["C1"])
    group = mc.generate_multichoice(n=3, seed=1)
    assert group.source == "bank/metachoice.md"
