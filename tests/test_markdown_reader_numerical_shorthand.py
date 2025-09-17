from __future__ import annotations
import textwrap


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_numerical_shorthand_scalar(tmp_path):
    # answer: 0.9
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N/Scalar
        answer: 0.9
        ---

        Any text
        """,
    )

    q_yaml = Reader(p).read()
    q_api = Q.Numerical("N/Scalar").ask(Text("Any text", format="markdown")).add_answer(0.9)
    assert q_yaml == q_api


def test_numerical_shorthand_mapping_with_tolerance(tmp_path):
    # answer: { value: 0.9, tolerance: 0 }
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N/WithTol
        answer:
          value: 0.9
          tolerance: 0
        ---

        Any text
        """,
    )

    q_yaml = Reader(p).read()
    q_api = Q.Numerical("N/WithTol").ask(Text("Any text", format="markdown")).add_answer(0.9, tolerance=0)
    assert q_yaml == q_api


def test_numerical_shorthand_with_feedback(tmp_path):
    # answer: { value: 0.9, tolerance: 0, feedback: correct }
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N/WithFB
        answer:
          value: 0.9
          tolerance: 0
          feedback: correct
        ---

        Any text
        """,
    )

    q_yaml = Reader(p).read()
    q_api = Q.Numerical("N/WithFB").ask(Text("Any text", format="markdown")).add_answer(0.9, tolerance=0, feedback="correct")
    assert q_yaml == q_api

