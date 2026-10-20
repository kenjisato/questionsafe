import pytest

from questionsafe import Q, Answer
from questionsafe.base import QuestionText


def _sc(*wrong: str):
    return (
        Q.SingleChoice(name="s1", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A")
        .set_choices_wrong(*wrong)
    )


def _wrong_fractions(q):
    return [float(a.fraction) for a in q.answers if float(a.fraction) <= 0]


@pytest.mark.parametrize(
    ("rule", "n_wrong", "expected"),
    [
        ("false2", 1, -50.0),
        ("false2", 2, -50.0),
        ("false2", 3, -33.33333),
        ("false2", 4, -25.0),
        ("false", 1, -100.0),
        ("false", 3, -33.33333),
        ("true", 3, -100.0),
        ("all", 3, -100.0),
        ("none", 3, 0.0),
    ],
)
def test_set_scoring_singlechoice(rule, n_wrong, expected):
    q = _sc(*"BCDE"[:n_wrong]).set_scoring(rule)
    assert _wrong_fractions(q) == [expected] * n_wrong
    q.validate()


def test_set_scoring_multichoice_true_uses_number_of_correct():
    mc = (
        Q.MultiChoice(name="m1", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A", "B")
        .set_choices_wrong("C", "D")
        .set_scoring("true")
    )
    assert _wrong_fractions(mc) == [-50.0, -50.0]
    mc.validate()


def test_set_scoring_keeps_positive_fractions():
    mc = (
        Q.MultiChoice(name="m1", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A", "B", "C")
        .set_choices_wrong("D")
        .set_scoring("false2")
    )
    assert [float(a.fraction) for a in mc.answers] == [33.33333, 33.33333, 33.33333, -50.0]


def test_set_scoring_none_resets_negative_fractions():
    q = _sc("B", "C").set_scoring("false2").set_scoring("none")
    assert _wrong_fractions(q) == [0.0, 0.0]


def test_set_scoring_rejects_unknown_rule():
    with pytest.raises(ValueError, match="rule"):
        _sc("B").set_scoring("half")


def test_set_scoring_raises_when_fraction_is_not_a_moodle_value():
    # 1/11 has no Moodle-supported fraction
    with pytest.raises(ValueError, match="Moodle"):
        _sc(*[f"W{i}" for i in range(11)]).set_scoring("false")


def test_singlechoice_cloze_keeps_negative_fractions():
    token = _sc("B", "C").set_scoring("false2").cloze()
    assert token == "{1:MC:=A~%-50.0%B~%-50.0%C}"


def test_cloze_set_scoring_applies_to_embedded_choice_questions():
    sc = _sc("B", "C")
    sc.name = "g1"
    mc = (
        Q.MultiChoice(name="g2", questiontext=QuestionText("<p>y</p>"))
        .set_answers(
            Answer.from_text("P", fraction=50),
            Answer.from_text("Q", fraction=50),
            Answer.from_text("R", fraction=0),
        )
    )
    num = Q.Numerical(name="g3").add_answer(1.0, tolerance=0.1)
    cz = Q.Cloze(name="c", questiontext=QuestionText("{{g1}} {{g2}} {{g3}}"))
    cz.embed_question(sc).embed_question(mc).embed_question(num)

    cz.set_scoring("false2")
    assert _wrong_fractions(sc) == [-50.0, -50.0]
    assert _wrong_fractions(mc) == [-50.0]
    assert "%-50.0%B" in cz.compile_text()
