from __future__ import annotations

from questionsafe import Q, render_xml
from questionsafe.base import Feedback, QuestionText
from questionsafe.writer.moodle._build import to_context
from questionsafe.writer.moodle.utils import escape_markdown_math


def test_escapes_markdown_specials_inside_math_only():
    src = r"Let \( a*b + x_1 \) and \[ \{x\} \] be *true*."
    assert escape_markdown_math(src) == (
        r"Let \\\( a\*b \+ x\_1 \\\) and \\\[ \\\{x\\\} \\\] be *true*."
    )


def test_display_math_spans_lines():
    src = "\\[\n a &= b \\\\\n c &= d\n\\]"
    assert escape_markdown_math(src) == "\\\\\\[\n a &= b \\\\\\\\\n c &= d\n\\\\\\]"


def test_escaped_backslash_is_not_a_math_delimiter():
    src = r"\\( not math \\)"
    assert escape_markdown_math(src) == src


def test_code_is_left_alone():
    src = "`\\( a*b \\)`\n\n```\n\\( a*b \\)\n```"
    assert escape_markdown_math(src) == src


def test_escaping_is_idempotent():
    src = r"\( a*b \) and \[ c_1 \]"
    once = escape_markdown_math(src)
    assert escape_markdown_math(once) == once


def test_markdown_texts_are_escaped_in_xml():
    q = Q.SingleChoice(name="M", questiontext=QuestionText(r"Let \( a*b \).", format="markdown"))
    q.set_choice_correct("A").set_choices_wrong("B")
    q.set_feedback_general(Feedback(r"Since \( x_1 \).", format="markdown"))
    xml = render_xml([q]).decode("utf-8")
    assert r"Let \\\( a\*b \\\)." in xml
    assert r"Since \\\( x\_1 \\\)." in xml


def test_html_texts_are_not_escaped():
    q = Q.SingleChoice(name="H", questiontext=QuestionText(r"<p>\( a*b \)</p>", format="html"))
    q.set_choice_correct("A").set_choices_wrong("B")
    xml = render_xml([q]).decode("utf-8")
    assert r"<p>\( a*b \)</p>" in xml


def test_escaping_is_xml_only():
    # The context is shared with the HTML preview; only the XML templates escape.
    q = Q.SingleChoice(name="P", questiontext=QuestionText(r"Let \( a*b \).", format="markdown"))
    q.set_choice_correct("A").set_choices_wrong("B")
    assert to_context([q])[0]["stem_text"] == r"Let \( a*b \)."


def test_cloze_escapes_stem_math_but_not_gaps():
    sc = Q.SingleChoice(name="g").set_choice_correct(r"\( a*b \)").set_choices_wrong("B")
    q = Q.Cloze(name="CZ", questiontext=QuestionText(r"Let \( x_1 \): {{g}}", format="markdown"))
    q.embed_question(sc)
    xml = render_xml([q]).decode("utf-8")
    assert r"Let \\\( x\_1 \\\):" in xml
    assert r"=\( a*b \)" in xml
