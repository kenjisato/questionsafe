from questionsafe import Q, Text, Answer
from questionsafe.quiz import Quiz
import pytest


def test_quiz_len_counts_questions_not_categories() -> None:
    quiz = Quiz(category="Course/Week1")
    # Initially empty
    assert len(quiz) == 0

    # Adding a category does not increase count
    quiz.add(Q.Category(path="Course/Intro"))
    assert len(quiz) == 0

    # Add a SingleChoice (counts as 1)
    sc = (
        Q.SingleChoice(name="SC", questiontext=Text("<p>Pick one</p>"))
        .set_choice_correct("A")
        .set_choices_wrong("B", "C")
    )
    quiz.add(sc)
    assert len(quiz) == 1

    # Add a ShortAnswer (counts as 1)
    sa = Q.ShortAnswer(name="SA", questiontext=Text("<p>Spell</p>")).add_answer(
        Answer.from_text("colour", fraction=100)
    )
    quiz.add(sa)
    assert len(quiz) == 2

    # add_group inserts a Category (not counted) and appends two questions
    tf = (
        Q.TrueFalse(name="TF", questiontext=Text("<p>T/F?</p>"))
        .set_choice_correct("true")
        .set_choice_wrong("false")
    )
    nu = Q.Numerical(name="NUM", questiontext=Text("<p>Num?</p>"))
    nu.answers.append(Answer.from_num(3.14, tolerance=0.01, fraction=100))

    quiz.add_group([tf, nu], idnumber_prefix="g-", idnumber_offset=0)
    assert len(quiz) == 4

    # Adding another category does not change the count
    quiz.add(Q.Category(path="Course/Week1/End"))
    assert len(quiz) == 4


def test_quiz_add_group_rejects_categories() -> None:
    quiz = Quiz(category="Course/Week2")
    sc = (
        Q.SingleChoice(name="SC2", questiontext=Text("<p>X</p>"))
        .set_choice_correct("A")
        .set_choices_wrong("B")
    )
    with pytest.raises(TypeError):
        quiz.add_group([Q.Category(path="Course/Week2/Sub"), sc])
