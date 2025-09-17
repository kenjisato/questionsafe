from __future__ import annotations
import textwrap


def _write(tmp_path, name: str, text: str):
    p = tmp_path / name
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_multichoice_checkbox_choices(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        "mc.md",
        """
        ---
        type: multichoice
        name: MC/Checkbox
        choices:
          - (x) A
          - (x) B
          - ( ) X
          - ( ) Y
        ---

        Body
        """,
    )

    q = Reader(p).read()
    # Equal to set_choices_correct(A,B) + set_choices_wrong(X,Y)
    q_py = (
        Q.MultiChoice("MC/Checkbox")
        .ask(Text("Body", format="markdown"))
        .set_choices_correct("A", "B")
        .set_choices_wrong("X", "Y")
    )
    assert q == q_py


def test_singlechoice_checkbox_choices(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        "sc.md",
        """
        ---
        type: singlechoice
        name: SC/Checkbox
        choices:
          - (x) A
          - ( ) B
          - ( ) C
        ---

        Body
        """,
    )

    q = Reader(p).read()
    q_py = (
        Q.SingleChoice("SC/Checkbox")
        .ask(Text("Body", format="markdown"))
        .set_choice_correct("A")
        .set_choices_wrong("B", "C")
    )
    assert q == q_py


def test_truefalse_checkbox_choices(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        "tf.md",
        """
        ---
        type: truefalse
        name: TF/Checkbox
        choices:
          - ( ) true
          - (x) false
        ---

        Body
        """,
    )

    q = Reader(p).read()
    q_py = Q.TrueFalse("TF/Checkbox").ask(Text("Body", format="markdown")).set_correct_if_false()
    assert q == q_py


def test_question_wrapper_mapping(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        "wrap.md",
        """
        ---
        question:
          type: singlechoice
          name: Wrapped
          choices:
            - (x) A
            - ( ) B
        ---

        Body
        """,
    )

    q = Reader(p).read()
    q_py = Q.SingleChoice("Wrapped").ask(Text("Body", format="markdown")).set_choice_correct("A").set_choices_wrong("B")
    assert q == q_py

