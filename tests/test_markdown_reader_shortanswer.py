from __future__ import annotations
import textwrap


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_shortanswer_shorthand_scalar(tmp_path):
    # answer: Tokyo
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: shortanswer
        name: SA/Scalar
        answer: Tokyo
        ---

        Capital of Japan?
        """,
    )

    q_yaml = Reader(p).read()
    q_api = Q.ShortAnswer("SA/Scalar").ask(Text("Capital of Japan?", format="markdown")).add_answer("Tokyo", fraction=100)
    assert q_yaml == q_api


def test_shortanswer_shorthand_mapping_with_feedback(tmp_path):
    # answer: { text: Tokyo, feedback: correct }
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: shortanswer
        name: SA/WithFB
        answer:
          text: Tokyo
          feedback: correct
        ---

        Capital of Japan?
        """,
    )

    q_yaml = Reader(p).read()
    q_api = Q.ShortAnswer("SA/WithFB").ask(Text("Capital of Japan?", format="markdown")).add_answer("Tokyo", fraction=100, feedback="correct")
    assert q_yaml == q_api


def test_shortanswer_answers_list_still_supported(tmp_path):
    # answers: [{text: Tokyo, fraction: 100}, {text: Osaka, fraction: 0}]
    from questionsafe import Reader, Q, Text, Answer

    p = _write(
        tmp_path,
        """
        ---
        type: shortanswer
        name: SA/List
        answers:
          - text: Tokyo
            fraction: 100
          - text: Osaka
            fraction: 0
        ---

        Capital of Japan?
        """,
    )

    q_yaml = Reader(p).read()
    q_api = (
        Q.ShortAnswer("SA/List")
        .ask(Text("Capital of Japan?", format="markdown"))
        .set_answers(Answer.from_text("Tokyo", fraction=100), Answer.from_text("Osaka", fraction=0))
    )
    assert q_yaml == q_api

