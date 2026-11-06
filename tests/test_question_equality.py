"""Question equality (#15).

Choice order is presentation, not content: choice questions are equal regardless of it.
ShortAnswer and Numerical are graded by the first matching answer, so order counts there.
"""
from __future__ import annotations

import copy
import textwrap

import pytest

from questionsafe import Answer, Q


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_equivalence_truefalse_shorthand(tmp_path):
    from questionsafe import Q, Reader, Text

    # Python API
    q_py = Q.TrueFalse(name="Logic/DeMorgan").ask(
        Text("True or False: Not(A and B) == (Not A) or (Not B)", format="markdown")
    ).set_correct_if_true()

    # Markdown shorthand
    p = _write(
        tmp_path,
        """
        ---
        type: truefalse
        name: Logic/DeMorgan
        answer: true
        tags: [logic]
        defaultgrade: 1.0
        ---

        True or False: Not(A and B) == (Not A) or (Not B)
        """,
    )
    q_md = Reader(p).read()

    # Align tags to avoid incidental mismatch
    q_py.set_tags("logic")

    assert q_py == q_md


def test_equivalence_singlechoice_choices(tmp_path):
    from questionsafe import Q, Reader, Text

    # Python API
    q_py = (
        Q.SingleChoice(name="Japan/Capital")
        .ask(Text("What is the capital of Japan?", format="markdown"))
        .set_choice_correct(Text("Tokyo", format="markdown"))
        .set_choices_wrong(Text("Osaka", format="markdown"), Text("Kyoto", format="markdown"), Text("Kanagawa", format="markdown"))
    )

    # Markdown shorthand
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Japan/Capital
        choices:
          correct: [Tokyo]
          wrong: [Osaka, Kyoto, Kanagawa]
        ---

        What is the capital of Japan?
        """,
    )
    q_md = Reader(p).read()

    assert q_py == q_md

def _mc(*wrong: str):
    return Q.MultiChoice(name="M", questiontext="Pick.").set_choices_correct("A", "B").set_choices_wrong(*wrong)


def _sc(*wrong: str):
    return Q.SingleChoice(name="S", questiontext="Pick.").set_choice_correct("A").set_choices_wrong(*wrong)


@pytest.mark.parametrize("make", [_mc, _sc])
def test_choice_order_does_not_matter(make):
    assert make("C", "D") == make("D", "C")


def test_truefalse_choice_order_does_not_matter():
    a = Q.TrueFalse(name="T", questiontext="?").set_correct_if_true()
    b = copy.deepcopy(a)
    b.answers.reverse()
    assert a == b


@pytest.mark.parametrize(
    "change",
    [
        lambda q: q.set_choices_wrong("C", "E"),
        lambda q: q.add_choice_wrong("D"),  # a duplicate choice is not the same question
        lambda q: q.set_numbering("123"),
        lambda q: q.set_shuffle(False),
        lambda q: q.set_single_choice(),
        lambda q: q.set_questiontext("Choose."),
        lambda q: q.set_defaultgrade(2),
    ],
)
def test_any_other_difference_matters(change):
    assert _mc("C", "D") != change(_mc("D", "C"))


def test_answer_fraction_and_feedback_matter():
    base = Q.MultiChoice(name="M", questiontext="Pick.")
    a = copy.deepcopy(base).add_answer("A", fraction=100).add_answer("B", fraction=0)
    assert a != copy.deepcopy(base).add_answer("A", fraction=100).add_answer("B", fraction=-50)
    assert a != copy.deepcopy(base).add_answer("A", fraction=100, feedback="Yes").add_answer("B", fraction=0)


def test_shortanswer_answer_order_matters():
    # Moodle grades by the first matching answer: '*' before 'Tokyo' changes the grade.
    a = Q.ShortAnswer(name="S", questiontext="?").add_answer("Tokyo").add_answer("*", fraction=0)
    b = Q.ShortAnswer(name="S", questiontext="?").add_answer("*", fraction=0).add_answer("Tokyo")
    assert a != b


def test_numerical_answer_order_matters():
    a = Q.Numerical(name="N", questiontext="?").add_answer(1, tolerance=0.5).add_answer(Answer.from_num(1, tolerance=2, fraction=50))
    b = Q.Numerical(name="N", questiontext="?").add_answer(Answer.from_num(1, tolerance=2, fraction=50)).add_answer(1, tolerance=0.5)
    assert a != b


def test_different_types_are_not_equal():
    sc = _sc("C")
    mc = Q.MultiChoice(name="S", questiontext="Pick.").set_single_choice()
    mc.set_answers(*copy.deepcopy(sc.answers))
    assert sc != mc
