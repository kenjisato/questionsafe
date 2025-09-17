import pytest

from questionsafe import Q, Answer
from questionsafe.base import QuestionText


def test_cloze_singlechoice_variants_and_weight():
    sc = (
        Q.SingleChoice(name="s1", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A")
        .set_choices_wrong("B")
    )

    t_mc = sc.cloze()  # default dropdown
    assert t_mc.startswith("{1:MC:")
    assert "=A" in t_mc and "~B" in t_mc

    t_mcv = sc.cloze(orientation="v", weight=2)
    assert t_mcv.startswith("{2:MCV:")

    t_mch = sc.cloze(orientation="h", weight=2)
    assert t_mch.startswith("{2:MCH:")



def test_cloze_multichoice_variants_default_and_horizontal():
    mc = Q.MultiChoice(name="m1", questiontext=QuestionText("<p>x</p>"))
    mc.set_answers(
        Answer.from_text("A", fraction=50),
        Answer.from_text("B", fraction=50),
        Answer.from_text("C", fraction=0),
    )

    t_default = mc.cloze()
    assert t_default.startswith("{1:MR:")

    t_mrh = mc.cloze(orientation="h")
    assert t_mrh.startswith("{1:MRH:")



def test_cloze_shortanswer_star_rule_and_case_flag():
    # valid with catch-all at the end
    sa = Q.ShortAnswer(name="sa1", questiontext=QuestionText("<p>x</p>"))
    sa.add_answer(Answer.from_text("ok", fraction=100))
    sa.add_answer(Answer.from_text("*", fraction=0))
    t = sa.cloze()
    assert t.startswith("{1:SHORTANSWER:")
    assert "~*}" in t or t.endswith("*}")

    # case sensitive variant
    sa2 = Q.ShortAnswer(name="sa2", questiontext=QuestionText("<p>x</p>"))
    sa2.set_usecase(1)
    sa2.add_answer(Answer.from_text("YES", fraction=100))
    t2 = sa2.cloze()
    assert t2.startswith("{1:SHORTANSWER_C:")

    # invalid: catch-all not last
    sa_bad = Q.ShortAnswer(name="sa3", questiontext=QuestionText("<p>x</p>"))
    sa_bad.add_answer(Answer.from_text("*", fraction=0))
    sa_bad.add_answer(Answer.from_text("no", fraction=0))
    with pytest.raises(ValueError):
        sa_bad.cloze()



def test_cloze_compile_text_and_duplicate_names():
    sc = (
        Q.SingleChoice(name="s", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A")
        .set_choices_wrong("B")
    )
    sa = Q.ShortAnswer(name="sa", questiontext=QuestionText("<p>x</p>"))
    sa.add_answer(Answer.from_text("ok", fraction=100))

    cl = Q.Cloze(
        name="C1",
        questiontext=QuestionText("<p>Choose {{ s }} and spell {{  sa }}</p>"),
    )
    cl.embed_question(sc, orientation="v").embed_question(sa)

    compiled = cl.compile_text()
    assert "{{ s }}" not in compiled and "{{  sa }}" not in compiled
    assert "{1:MCV:" in compiled
    assert "{1:SHORTANSWER:" in compiled or "{1:SHORTANSWER_C:" in compiled

    # duplicate embedding names rejected
    with pytest.raises(ValueError):
        cl.embed_question(sc)



def test_cloze_embed_weight_validation_and_empty_answer_guard():
    sc_ok = (
        Q.SingleChoice(name="s2", questiontext=QuestionText("<p>x</p>"))
        .set_choices_correct("A")
        .set_choices_wrong("B")
    )
    cl = Q.Cloze(name="C2", questiontext=QuestionText("<p>{{  s2 }}</p>"))

    # weight must be nonnegative integer
    cl.embed_question(sc_ok, weight=0)  # allowed

    cl2 = Q.Cloze(name="C2b", questiontext=QuestionText("<p>{{ s2 }}</p>"))
    with pytest.raises(ValueError):
        cl2.embed_question(sc_ok, weight=-1)

    cl3 = Q.Cloze(name="C2c", questiontext=QuestionText("<p>{{ s2 }}</p>"))
    with pytest.raises(TypeError):
        cl3.embed_question(sc_ok, weight=1.5)  # non-integer not allowed

    # empty answer text should raise on encode
    sc_bad = Q.SingleChoice(name="s3", questiontext=QuestionText("<p>x</p>"))
    sc_bad.add_choice_correct("")
    with pytest.raises(ValueError):
        sc_bad.cloze()

