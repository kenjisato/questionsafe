import math
import pytest

from questionsafe import Q, Answer
from questionsafe.base import QuestionText


def positives(answers):
    return [a for a in answers if float(a.fraction) > 0]


def nonpositives(answers):
    return [a for a in answers if float(a.fraction) <= 0]


def test_add_choice_correct_first_adds_100():
    q = Q.MultiChoice(name="MC/add1", questiontext=QuestionText("Q"))
    q.add_choice_correct("A")
    pos = positives(q.answers)
    assert len(pos) == 1
    assert math.isclose(pos[0].fraction, 100.0, rel_tol=1e-6, abs_tol=1e-6)


def test_add_choice_correct_recalculates_uniform_two_to_three():
    q = Q.MultiChoice(name="MC/add2", questiontext=QuestionText("Q"))
    q.set_choices_correct("A", "B")  # -> 50 each
    q.add_choice_correct("C")          # -> 33.33333 each if allowed
    pos = positives(q.answers)
    assert len(pos) == 3
    expected = 100.0 / 3.0
    assert all(math.isclose(a.fraction, expected, rel_tol=1e-6, abs_tol=1e-6) for a in pos)


def test_add_choice_correct_uniform_to_11_raises_when_not_allowed():
    q = Q.MultiChoice(name="MC/add3", questiontext=QuestionText("Q"))
    q.set_choices_correct(*[f"C{i}" for i in range(10)])  # -> 10 each
    with pytest.raises(ValueError):
        q.add_choice_correct("C10")  # 100/11 not in allowed list


def test_add_choice_correct_nonuniform_raises():
    q = Q.MultiChoice(name="MC/add4", questiontext=QuestionText("Q"))
    q.set_answers(
        Answer.from_text("A", fraction=60),
        Answer.from_text("B", fraction=40),
    )
    with pytest.raises(ValueError):
        q.add_choice_correct("C")
