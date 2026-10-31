from __future__ import annotations

import textwrap

import pytest

from questionsafe import Q, Reader, Text


def _write(tmp_path, text: str):
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_singlechoice_choices_section(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: AS
        ---

        Which statement is correct?

        ## /choices

        - (x) A
        - ( ) B
        - ( ) C
        """,
    )
    want = (
        Q.SingleChoice("AS")
        .ask(Text("Which statement is correct?", format="markdown"))
        .set_choice_correct("A")
        .set_choices_wrong("B", "C")
    )
    assert Reader(p).read() == want


def test_multichoice_choices_section_any_heading_level(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: multichoice
        name: MC
        ---

        Body

        ### /choices
        - (x) A
        - (x) B
        - ( ) X
        """,
    )
    want = (
        Q.MultiChoice("MC")
        .ask(Text("Body", format="markdown"))
        .set_choices_correct("A", "B")
        .set_choices_wrong("X")
    )
    assert Reader(p).read() == want


def test_choice_continues_on_indented_lines(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Long
        ---

        Body

        ## /choices

        - (x) The AS curve slopes upward
          because some prices are sticky.
        - ( ) B
        """,
    )
    q = Reader(p).read()
    texts = [str(a.text) for a in q.answers]
    assert texts[0] == "The AS curve slopes upward\nbecause some prices are sticky."


def test_noqs_heading_stays_in_question_text(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Noqs
        ---

        Intro

        ## /choices {.noqs}

        Still question text.

        ## /choices

        - (x) A
        - ( ) B
        """,
    )
    q = Reader(p).read()
    assert q.questiontext.text == "Intro\n\n## /choices\n\nStill question text."
    assert len(q.answers) == 2


def test_heading_inside_code_fence_is_not_reserved(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Fence
        ---

        ```
        ## /unknown
        ```

        ## /choices

        - (x) A
        - ( ) B
        """,
    )
    q = Reader(p).read()
    assert "## /unknown" in q.questiontext.text


def test_both_front_matter_and_section_is_an_error(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Both
        choices:
          - (x) A
          - ( ) B
        ---

        Body

        ## /choices

        - (x) A
        - ( ) B
        """,
    )
    with pytest.raises(ValueError, match="both"):
        Reader(p).read()


def test_unknown_section_is_an_error(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Unknown
        ---

        Body

        ## /not-a-section

        Nice.
        """,
    )
    with pytest.raises(ValueError, match="/not-a-section"):
        Reader(p).read()


def test_non_list_content_in_choices_is_an_error(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Para
        ---

        Body

        ## /choices

        Some paragraph.
        - (x) A
        """,
    )
    with pytest.raises(ValueError, match="/choices"):
        Reader(p).read()


def test_choices_section_on_unsupported_type_is_an_error(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: essay
        name: Essay
        ---

        Body

        ## /choices

        - (x) A
        """,
    )
    with pytest.raises(ValueError, match="essay"):
        Reader(p).read()


def test_choices_section_accepts_o_as_correct(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: multichoice
        name: O
        ---

        Body

        ## /choices

        - (o) A
        - (O) B
        - ( ) X
        """,
    )
    want = (
        Q.MultiChoice("O")
        .ask(Text("Body", format="markdown"))
        .set_choices_correct("A", "B")
        .set_choices_wrong("X")
    )
    assert Reader(p).read() == want


def test_unmarked_choice_is_an_error(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: singlechoice
        name: Unmarked
        ---

        Body

        ## /choices

        - (x) A
        - B
        """,
    )
    with pytest.raises(ValueError, match=r"\(o\)"):
        Reader(p).read()
