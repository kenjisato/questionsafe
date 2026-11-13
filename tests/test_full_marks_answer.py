"""ShortAnswer and Numerical need an answer worth 100% (#17).

Moodle's edit forms reject a question without one (`fractionsnomax`), since no response
could then get full marks.
"""
import pytest

from questionsafe import Answer, Q


def test_shortanswer_without_full_marks_answer_fails():
    q = Q.ShortAnswer(name="SA", questiontext="Capital?").add_answer("Tokyo", fraction=50)
    with pytest.raises(ValueError, match="100%"):
        q.validate()


def test_shortanswer_with_full_marks_and_partial_answers_passes():
    Q.ShortAnswer(name="SA", questiontext="Capital?").add_answer("Tokyo").add_answer(
        "Edo", fraction=50
    ).validate()


def test_numerical_without_full_marks_answer_fails():
    q = Q.Numerical(name="N", questiontext="?").add_answer(Answer.from_num(1, tolerance=2, fraction=50))
    with pytest.raises(ValueError, match="100%"):
        q.validate()


def test_numerical_with_full_marks_and_partial_answers_passes():
    Q.Numerical(name="N", questiontext="?").add_answer(1, tolerance=0.5).add_answer(
        Answer.from_num(1, tolerance=2, fraction=50)
    ).validate()
