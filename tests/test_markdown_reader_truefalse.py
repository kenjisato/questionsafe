from __future__ import annotations
import textwrap


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_reader_truefalse_shorthand_true(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: truefalse
        name: Logic/DeMorgan
        answer: true
        tags: [logic]
        ---

        Not(A and B) == (Not A) or (Not B)
        """,
    )

    q = Reader(p).read()
    assert isinstance(q, Q.TrueFalse)
    assert q.name == "Logic/DeMorgan"
    # question text treated as markdown by default
    assert q.questiontext.format == "markdown"
    assert "Not(A and B)" in q.questiontext.text

    texts = [a.text.strip().lower() for a in q.answers]
    assert set(texts) == {"true", "false"}
    # 'true' should be the correct (100), 'false' wrong (0)
    true_ans = next(a for a in q.answers if a.text.strip().lower() == "true")
    false_ans = next(a for a in q.answers if a.text.strip().lower() == "false")
    assert float(true_ans.fraction) == 100.0
    assert float(false_ans.fraction) <= 0.0

    assert q.tags == ["logic"]

    # Assert semantic equivalence with Python API
    q_py = (
        Q.TrueFalse(name="Logic/DeMorgan")
        .ask(Text("Not(A and B) == (Not A) or (Not B)", format="markdown"))
        .set_correct_if_true()
        .set_tags("logic")
    )
    assert q_py == q


def test_reader_truefalse_shorthand_false(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: truefalse
        name: Math/Claim
        answer: false
        ---

        1 is an even number.
        """,
    )

    q = Reader(p).read()
    assert isinstance(q, Q.TrueFalse)
    texts = [a.text.strip().lower() for a in q.answers]
    assert set(texts) == {"true", "false"}
    # 'false' should be the correct (100)
    false_ans = next(a for a in q.answers if a.text.strip().lower() == "false")
    assert float(false_ans.fraction) == 100.0

    # Assert semantic equivalence with Python API
    q_py = (
        Q.TrueFalse(name="Math/Claim")
        .ask(Text("1 is an even number.", format="markdown"))
        .set_correct_if_false()
    )
    assert q_py == q

