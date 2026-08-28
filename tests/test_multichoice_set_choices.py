import math

import pytest

from questionsafe.questions import MultiChoice
from questionsafe.base import QuestionText
from questionsafe import Answer


def positives(answers):
    return [a for a in answers if float(a.fraction) > 0]


def nonpositives(answers):
    return [a for a in answers if float(a.fraction) <= 0]


def test_set_choices_correct_replaces_only_positive_and_distributes_uniformly():
    q = MultiChoice(name="MC", questiontext=QuestionText("Q"))
    # Start with 1 correct and 2 wrong
    q.add_answer(Answer.from_text("old-correct", fraction=100))
    q.add_answer(Answer.from_text("w1", fraction=0))
    q.add_answer(Answer.from_text("w2", fraction=-33.33333))

    q.set_choices_correct("C1", "C2")

    pos = positives(q.answers)
    neg = nonpositives(q.answers)

    # Wrong/neutral answers remain
    assert {a.text for a in neg} == {"w1", "w2"}

    # Positives are replaced by two new, uniform 50 each
    assert len(pos) == 2
    assert {a.text for a in pos} == {"C1", "C2"}
    assert math.isclose(sum(a.fraction for a in pos), 100.0, rel_tol=1e-6, abs_tol=1e-6)
    for a in pos:
        assert math.isclose(a.fraction, 50.0, rel_tol=1e-6, abs_tol=1e-6)


def test_set_choices_wrong_replaces_only_nonpositive_with_fraction():
    q = MultiChoice(name="MC2", questiontext=QuestionText("Q"))
    # Start with two correct and two wrong
    q.add_answer(Answer.from_text("C1", fraction=60))
    q.add_answer(Answer.from_text("C2", fraction=40))
    q.add_answer(Answer.from_text("w1", fraction=0))
    q.add_answer(Answer.from_text("w2", fraction=-10))

    q.set_choices_wrong("WNEW1", "WNEW2", fraction=-25.0)

    pos = positives(q.answers)
    neg = nonpositives(q.answers)

    # Positives remain untouched
    assert {a.text for a in pos} == {"C1", "C2"}
    # Negatives replaced with two new wrongs of provided fraction
    assert {a.text for a in neg} == {"WNEW1", "WNEW2"}
    for a in neg:
        assert a.fraction == -25.0


def test_set_choices_correct_three_way_snaps_and_validates():
    # Safe API contract: after a chain of safe calls, validate() passes.
    # 100/3 must snap to Moodle's 33.33333, not stay at 33.3333333...
    q = MultiChoice(name="MC4", questiontext=QuestionText("Q"))
    q.set_choices_correct("C1", "C2", "C3")
    q.set_choices_wrong("w1")
    q.validate()
    for a in positives(q.answers):
        assert a.fraction == 33.33333


def test_set_choices_correct_unsplittable_raises():
    q = MultiChoice(name="MC5", questiontext=QuestionText("Q"))
    # 100/11 has no Moodle-supported value to snap to
    with pytest.raises(ValueError, match="set_answers"):
        q.set_choices_correct(*[f"C{i}" for i in range(11)])


def test_set_choices_correct_with_no_texts_removes_positives():
    q = MultiChoice(name="MC3", questiontext=QuestionText("Q"))
    q.add_answer(Answer.from_text("C1", fraction=100))
    q.add_answer(Answer.from_text("w1", fraction=0))

    q.set_choices_correct()  # remove positives

    assert all(float(a.fraction) <= 0 for a in q.answers)
    assert {a.text for a in q.answers} == {"w1"}
