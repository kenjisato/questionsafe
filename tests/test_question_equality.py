from __future__ import annotations
import textwrap


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
        .set_choice_correct("Tokyo")
        .set_choices_wrong("Osaka", "Kyoto", "Kanagawa")
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

