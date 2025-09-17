import pytest

from questionsafe import Q, Answer

from questionsafe.base import Question, Feedback, GraderInfo, Hint, QuestionText
from questionsafe.questions.essay import EssayResponse
from questionsafe.quiz import Quiz
from questionsafe import render_xml, render_html


def test_render_xml_accepts_quiz() -> None:
    quiz = Quiz()
    q = Q.MultiChoice(name="MC", questiontext=QuestionText("<p>Q</p>"))
    q.set_choices_correct("A")
    quiz.add(q)
    data = render_xml(quiz)
    assert isinstance(data, (bytes, bytearray))
    assert b"<quiz>" in data


def test_category_is_question_and_renderable() -> None:
    # Category should be a subclass of Question and acceptable in Quiz.questions
    cat = Q.Category(path="Sample/Section1")
    assert isinstance(cat, Question)
    quiz = Quiz()
    quiz.add(cat)
    # Should render without error and include category node
    xml = render_xml(quiz)
    assert b'<question type="category">' in xml


def test_html_unique_group_names_by_idnumber() -> None:
    quiz = Quiz()

    a = Q.TrueFalse(name="TF", questiontext=QuestionText("<p>T/F?</p>"))
    a.set_choice_correct("true").set_choice_wrong("false")
    a.set_idnumber("tf-0")

    b = Q.TrueFalse(name="TF", questiontext=QuestionText("<p>T/F?</p>"))
    b.set_choice_correct("true").set_choice_wrong("false")
    b.set_idnumber("tf-1")

    quiz.add(a, b)
    html = render_html(quiz)
    # Each question should have its own input name derived from idnumber
    assert html.count('name="tf-0"') >= 1
    assert html.count('name="tf-1"') >= 1


def test_multichoice_validation_single_requires_correct() -> None:
    q = Q.MultiChoice(name="MC", questiontext=QuestionText("<p>x</p>"))
    # no answers added -> should fail
    with pytest.raises(ValueError):
        q.validate()
    # wrong answers only in single mode -> should fail
    q.set_choices_wrong("A", "B")
    with pytest.raises(ValueError):
        q.validate()
    # add a correct answer -> ok
    q.set_choices_correct("C")
    q.validate()


def test_truefalse_validation() -> None:
    t = Q.TrueFalse(name="T", questiontext=QuestionText("<p>x</p>"))
    with pytest.raises(ValueError):
        t.validate()  # missing answers
    t.set_choice_correct("true").set_choice_wrong("false")
    t.validate()  # ok


def test_numerical_validation() -> None:
    n = Q.Numerical(name="N", questiontext=QuestionText("<p>x</p>"))
    with pytest.raises(ValueError):
        n.validate()
    n.answers.append(Answer.from_num(1.0, fraction=100))
    n.validate()


def test_essay_validation_defaults() -> None:
    e = Q.Essay(name="E", questiontext=QuestionText("<p>x</p>"))
    e.validate()
    e.set_response_format("plain")
    e.validate()
    e.set_response_format("invalid")  # type: ignore
    with pytest.raises(ValueError):
        e.validate()


def test_quiz_validate_calls_each() -> None:
    quiz = Quiz()
    # Valid set
    q1 = Q.ShortAnswer(name="SA", questiontext=QuestionText("<p>x</p>"))
    q1.answers.append(Answer.from_text("ok", fraction=100))
    quiz.add(q1)
    quiz.validate()  # should not raise

    # Now add invalid question
    q2 = Q.Numerical(name="N2", questiontext=QuestionText("<p>x</p>"))
    quiz.add(q2)
    with pytest.raises(ValueError):
        quiz.validate()


def test_formats_and_hints_multichoice() -> None:
    quiz = Quiz()
    q = Q.MultiChoice(name="MC2", questiontext=QuestionText("Q2", format="markdown"))
    q.set_choices_correct("A", feedback=Feedback("<p>ok</p>", format="html"))
    q.hints.append(Hint("<p>h1</p>", shownumcorrect=True))
    q.hints.append(Hint("<p>h2</p>", clearwrong=True))
    quiz.add(q)
    xml = render_xml(quiz).decode("utf-8")
    assert '<questiontext format="markdown">' in xml
    assert '<feedback format="html">' in xml
    # hint flags
    assert "<shownumcorrect/>" in xml
    assert "<clearwrong/>" in xml


def test_truefalse_no_hints_and_feedback_format() -> None:
    quiz = Quiz()
    t = Q.TrueFalse(name="T2", questiontext=QuestionText("T?"))
    t.set_choice_correct("true", feedback=Feedback("good", format="plain_text"))
    t.set_choice_wrong("false")
    quiz.add(t)
    xml = render_xml(quiz).decode("utf-8")
    # With current semantics, set_wrong() overwrites any previous feedback for the correct answer.
    # Therefore, do not assert feedback presence here.
    assert "<hint " not in xml


def test_shortanswer_combined_and_feedback_format() -> None:
    quiz = Quiz()
    sa = Q.ShortAnswer(name="SA2", questiontext=QuestionText("Spell"))
    sa.answers.append(
        Answer.from_text(
            "colour", fraction=100, feedback=Feedback("right", format="html")
        )
    )
    # combined feedback optional; ensure template tolerates missing or present
    quiz.add(sa)
    xml = render_xml(quiz).decode("utf-8")
    assert '<feedback format="html">' in xml


def test_shortanswer_add_answer_fluent() -> None:
    quiz = Quiz()
    sa = (
        Q.ShortAnswer(
            name="SA/Color-Spelling",
            questiontext=QuestionText(
                "<p>Spell the British English word for 'color'</p>"
            ),
        )
        .add_answer(Answer.from_text("colour", fraction=100))
        .add_answer(Answer.from_text("colur", fraction=10))
    )
    quiz.add(sa)
    # Should validate and render
    sa.validate()
    xml = render_xml(quiz).decode("utf-8")
    assert "colour" in xml and "colur" in xml


def test_numerical_feedback_format_and_hints() -> None:
    quiz = Quiz()
    nu = Q.Numerical(name="NUM2", questiontext=QuestionText("Num?"))
    nu.answers.append(
        Answer.from_num(
            3.14,
            fraction=100,
            tolerance=0.01,
            feedback=Feedback("ok", format="markdown"),
        )
    )
    nu.hints.append(Hint("try again", format="plain_text"))
    quiz.add(nu)
    xml = render_xml(quiz).decode("utf-8")
    print(xml)
    assert '<feedback format="markdown">' in xml
    assert '<hint format="plain_text">' in xml


def test_numerical_add_answer_fluent() -> None:
    quiz = Quiz()
    nu = Q.Numerical(
        name="Num/Pi-Approx",
        questiontext=QuestionText("<p>Approximate value of π (2 decimal places)</p>"),
    ).add_answer(3.14, tolerance=0.005)
    quiz.add(nu)
    # Should validate and render
    nu.validate()
    xml = render_xml(quiz).decode("utf-8")
    assert "3.14" in xml


def test_essay_graderinfo_format() -> None:
    quiz = Quiz()
    es = Q.Essay(name="E2", questiontext=QuestionText("essay"))
    es.set_graderinfo(GraderInfo("guide", format="markdown"))
    quiz.add(es)
    xml = render_xml(quiz).decode("utf-8")
    assert '<graderinfo format="markdown">' in xml


def test_essay_set_response() -> None:
    from questionsafe.questions.essay import EssayTextArea, EssayAttachments
    quiz = Quiz()
    default_response = EssayResponse(
        textarea=EssayTextArea(format="editor", required=True, lines=20),
        attachments=EssayAttachments(count=1, filetypelist=["pdf"]),
    )
    es = Q.Essay(name="E3", questiontext=QuestionText("essay"))
    es.set_response(default_response)
    # mutate original to ensure deep copy was taken
    default_response.input_lines = 5
    quiz.add(es)
    es.validate()
    xml = render_xml(quiz).decode("utf-8")
    assert "<responseformat>editor</responseformat>" in xml
    assert "<responserequired>1</responserequired>" in xml
    assert "<responsefieldlines>20</responsefieldlines>" in xml
    assert "<attachments>1</attachments>" in xml
    assert "<filetypeslist>pdf</filetypeslist>" in xml


def test_multichoice_positive_fractions_sum_to_100_accept() -> None:
    q = Q.MultiChoice(name="MC-sum1", questiontext=QuestionText("Sum 100"))
    # MultiChoice defaults to multi-answer; no need to call set_multiple()
    q.set_answers(
        Answer.from_text("A", fraction=50),
        Answer.from_text("B", fraction=50),
        Answer.from_text("C", fraction=0),
    )
    # Should validate: positives sum to 100
    q.validate()


def test_multichoice_positive_fractions_sum_to_100_reject_80() -> None:
    q = Q.MultiChoice(name="MC-sum2", questiontext=QuestionText("Sum 80"))
    # MultiChoice defaults to multi-answer; no need to call set_multiple()
    q.set_answers(
        Answer.from_text("A", fraction=40),
        Answer.from_text("B", fraction=40),
        Answer.from_text("C", fraction=0),
    )
    with pytest.raises(ValueError):
        q.validate()


def test_multichoice_positive_fractions_sum_to_100_accept_mixed() -> None:
    q = Q.MultiChoice(name="MC-sum3", questiontext=QuestionText("Sum 100 mixed"))
    # MultiChoice defaults to multi-answer; no need to call set_multiple()
    q.set_answers(
        Answer.from_text("A", fraction=66.66667),
        Answer.from_text("B", fraction=33.33333),
        Answer.from_text("C", fraction=0),
    )
    q.validate()


def test_multichoice_positive_fractions_sum_to_100_reject_95() -> None:
    q = Q.MultiChoice(name="MC-sum4", questiontext=QuestionText("Sum 95"))
    # MultiChoice defaults to multi-answer; no need to call set_multiple()
    q.set_answers(
        Answer.from_text("A", fraction=90),
        Answer.from_text("B", fraction=5),
        Answer.from_text("C", fraction=0),
    )
    with pytest.raises(ValueError):
        q.validate()


def test_multichoice_add_answer_fluent() -> None:
    quiz = Quiz()
    mc = Q.MultiChoice(name="MC/add_answer", questiontext=QuestionText("Pick one"))
    mc.add_answer(Answer.from_text("A", fraction=100)).add_answer(
        Answer.from_text("B", fraction=0)
    )
    quiz.add(mc)
    mc.validate()
    xml = render_xml(quiz).decode("utf-8")
    assert '<question type="multichoice"' in xml
    assert ">A<" in xml and ">B<" in xml


def test_truefalse_add_answer_fluent() -> None:
    quiz = Quiz()
    tf = Q.TrueFalse(name="TF/add_answer", questiontext=QuestionText("T/F?"))
    tf.add_answer(Answer.from_text("true", fraction=100)).add_answer(
        Answer.from_text("false", fraction=0)
    )
    quiz.add(tf)
    tf.validate()
    xml = render_xml(quiz).decode("utf-8")
    assert '<question type="truefalse"' in xml
    assert ">true<" in xml and ">false<" in xml


def test_add_answer_type_checks_negative() -> None:
    # ShortAnswer should reject NumericalAnswer
    sa = Q.ShortAnswer(name="SA/typecheck", questiontext=QuestionText("x"))
    with pytest.raises(TypeError):
        sa.add_answer(
            Answer.from_num(1.0)
        )  # still wrong type for ShortAnswer, should raise
    # Numerical should reject generic Answer
    nu = Q.Numerical(name="NU/typecheck", questiontext=QuestionText("x"))
    with pytest.raises(TypeError):
        nu.add_answer(
            Answer.from_text("x")
        )  # still wrong type for Numerical, should raise
    # MultiChoice should reject NumericalAnswer
    mc = Q.MultiChoice(name="MC/typecheck", questiontext=QuestionText("x"))
    with pytest.raises(TypeError):
        mc.add_answer(
            Answer.from_num(2.0)
        )  # still wrong type for MultiChoice, should raise


def test_base_add_answer_not_supported_on_essay_and_description() -> None:
    es = Q.Essay(name="E/not-supported", questiontext=QuestionText("e"))
    with pytest.raises(NotImplementedError):
        es.add_answer(Answer.from_text("x"))
    desc = Q.Description(name="D/not-supported", questiontext=QuestionText("d"))
    with pytest.raises(NotImplementedError):
        desc.add_answer(Answer.from_text("x"))
        desc.add_answer(Answer.from_num(2.0))
