"""Texts keep the author's format through to the XML (#8)."""
from __future__ import annotations

import re
import textwrap

from questionsafe import Q, Reader, Text, render_xml


def _write(tmp_path, text: str, name: str = "q.md"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def _answers(xml: bytes) -> list[tuple[str, str]]:
    return re.findall(r'<answer fraction="[^"]+" format="([^"]+)">\s*<text>([^<]*)</text>', xml.decode())


def _feedback_formats(xml: bytes) -> list[str]:
    return re.findall(r'<feedback format="([^"]+)">', xml.decode())


def test_multichoice_writes_the_choice_format():
    q = Q.MultiChoice(name="M").set_choices_correct(Text(r"**A** \( a*b \)", format="markdown"))
    q.set_choices_wrong("B")
    assert set(_answers(render_xml([q]))) == {("markdown", r"**A** \\\( a\*b \\\)"), ("html", "B")}


def test_singlechoice_accepts_text_choices():
    q = Q.SingleChoice(name="S", questiontext="Pick.").set_choice_correct(Text(" **A** ", format="markdown"))
    q.add_choice_wrong("B")
    assert [(a.text, a.format) for a in q.answers] == [("**A**", "markdown"), ("B", "html")]
    q.validate()


SC = """
---
type: singlechoice
name: S
feedback:
  general: See **notes**.
{extra}---

Pick one.

## /choices

- (x) **A**
- ( ) B
"""


def test_reader_choices_and_feedback_inherit_markdown(tmp_path):
    q = Reader(_write(tmp_path, SC.format(extra=""))).read()
    assert [(a.text, a.format) for a in q.answers] == [("**A**", "markdown"), ("B", "markdown")]
    assert q.feedback_general.format == "markdown"
    assert [f for f, _ in _answers(render_xml([q]))] == ["markdown", "markdown"]


def test_reader_texts_follow_the_file_format(tmp_path):
    q = Reader(_write(tmp_path, SC.format(extra="format: html\n"))).read()
    assert {a.format for a in q.answers} == {"html"}
    assert q.feedback_general.format == "html"


def test_reader_front_matter_choices_inherit_markdown(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: multichoice
        name: M
        choices:
          correct: ["**A**"]
          wrong: [B]
        ---

        Pick.
        """,
    )
    assert {a.format for a in Reader(p).read().answers} == {"markdown"}


def test_reader_full_form_answers_and_hints_inherit_markdown(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: multichoice
        name: M
        answers:
          - text: "**A**"
            fraction: 100
            feedback: Because *A*.
          - text: B
            fraction: 0
        hints:
          - Think *twice*.
        feedback:
          correct: Well *done*.
        ---

        Pick.
        """,
    )
    q = Reader(p).read()
    assert {a.format for a in q.answers} == {"markdown"}
    assert q.answers[0].feedback.format == "markdown"
    assert q.hints[0].format == "markdown"
    assert q.feedback_correct.format == "markdown"
    assert set(_feedback_formats(render_xml([q]))) == {"markdown"}


def test_reader_metachoice_pool_inherits_markdown(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: metachoice
        name: MC
        choices:
          A: "**A**"
          B: B
          C: C
        stems:
          S: Pick *one*.
        ---

        ```csv
        choice,S
        A,x
        ```
        """,
    )
    group = Reader(p).read_metachoice().generate_singlechoice(n=2, limit=1, seed=1)
    (q,) = group
    assert {a.format for a in q.answers} == {"markdown"}
    assert q.questiontext.format == "markdown"


def test_reader_graderinfo_inherits_markdown(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: essay
        name: E
        graderinfo: Look for *x*.
        ---

        Explain.
        """,
    )
    gi = Reader(p).read().graderinfo
    assert (gi.text, gi.format) == ("Look for *x*.", "markdown")
