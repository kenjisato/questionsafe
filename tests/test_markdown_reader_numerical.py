from __future__ import annotations
import textwrap


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_numerical_reader_matches_api_sum(tmp_path):
    # YAML with exact string "0.9" should match API value computed as 0.3+0.3+0.3
    from questionsafe import Reader, Q

    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N/Exact
        answers:
          - value: "0.9"
            tolerance: 0
        ---

        Any text
        """,
    )

    q_yaml = Reader(p).read()

    from questionsafe import Text
    q_api = (
        Q.Numerical(name="N/Exact")
        .ask(Text("Any text", format="markdown"))
        .add_answer(0.3 + 0.3 + 0.3, tolerance=0)
    )

    assert q_yaml == q_api

