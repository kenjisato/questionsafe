"""Single-answer MultiChoice follows Moodle's form validation (#13).

single: the highest fraction must be 100%; the sum is not checked.
multiple: positive fractions must sum to 100%.
"""
import pytest

from questionsafe import Answer, Q


def _mc(*fractions, single):
    q = Q.MultiChoice(name="M", questiontext="Pick.").set_single_choice(single)
    for i, f in enumerate(fractions):
        q.add_answer(Answer.from_text(f"C{i}", fraction=f))
    return q


def test_single_allows_partial_credit_beyond_100_total():
    _mc(100, 50, 0, single=True).validate()


def test_single_needs_a_100_percent_answer():
    with pytest.raises(ValueError, match="fraction=100"):
        _mc(50, 50, 0, single=True).validate()


def test_multiple_still_needs_positive_fractions_to_sum_to_100():
    with pytest.raises(ValueError, match="Sum of positive fractions"):
        _mc(100, 50, 0, single=False).validate()


def test_singlechoice_still_allows_only_one_positive_answer():
    q = Q.SingleChoice(name="S", questiontext="Pick.")
    for t, f in [("A", 100), ("B", 50), ("C", 0)]:
        q.add_answer(Answer.from_text(t, fraction=f))
    with pytest.raises(ValueError, match="exactly one correct"):
        q.validate()
