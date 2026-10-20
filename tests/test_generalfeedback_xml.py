from questionsafe import Q, render_xml
from questionsafe.base import QuestionText, Feedback


def test_multichoice_generalfeedback_written():
    q = Q.MultiChoice(name="MC-GF", questiontext=QuestionText("<p>Q</p>"))
    q.set_choices_correct("A").set_choices_wrong("B")
    q.set_feedback_general(Feedback("GF-MC", format="markdown"))
    xml = render_xml([q]).decode("utf-8")
    assert '<generalfeedback format="markdown">' in xml
    assert "GF-MC" in xml


def test_singlechoice_generalfeedback_written():
    q = Q.SingleChoice(name="SC-GF", questiontext=QuestionText("<p>Q</p>"))
    q.set_choice_correct("A").set_choices_wrong("B")
    q.set_feedback_general(Feedback("GF-SC", format="html"))
    xml = render_xml([q]).decode("utf-8")
    assert '<generalfeedback format="html">' in xml
    assert "GF-SC" in xml


def test_cloze_generalfeedback_written():
    sc = Q.SingleChoice(name="g1").set_choices_correct("A").set_choices_wrong("B")
    q = Q.Cloze(name="CZ-GF", questiontext=QuestionText("<p>{{g1}}</p>")).embed_question(sc)
    q.set_feedback_general(Feedback("GF-CZ", format="html"))
    xml = render_xml([q]).decode("utf-8")
    assert '<generalfeedback format="html">' in xml
    assert "GF-CZ" in xml
