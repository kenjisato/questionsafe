from __future__ import annotations
import textwrap

def test_reader_singlechoice_file(tmp_path):
    from questionsafe import Reader, Q, Text
    md_text = textwrap.dedent(
        """
        ---
        type: singlechoice
        name: Japan/Capital
        choices:
          correct:
            - Tokyo
          wrong:
            - Osaka
            - Kyoto
            - Kanagawa
        tags:
          - Japan
        ---

        What is the capital of Japan?
        """
    ).strip()
    p = tmp_path / "q.md"
    p.write_text(md_text, encoding="utf-8")

    q = Reader(p).read()
    assert isinstance(q, Q.SingleChoice)
    assert q.name == "Japan/Capital"
    # question text treated as markdown by default
    assert q.questiontext.format == "markdown"
    assert "capital of Japan" in q.questiontext.text

    positives = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) > 0]
    assert len(positives) == 1 and positives[0].text.strip() == "Tokyo"

    wrongs = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) <= 0]
    wrong_texts = {a.text.strip() for a in wrongs}
    assert {"Osaka", "Kyoto", "Kanagawa"}.issubset(wrong_texts)

    assert q.tags == ["Japan"]

    # Also assert semantic equivalence with Python-constructed API
    q_py = (
        Q.SingleChoice(name="Japan/Capital")
        .ask(Text("What is the capital of Japan?", format="markdown"))
        .set_choice_correct("Tokyo")
        .set_choices_wrong("Osaka", "Kyoto", "Kanagawa")
        .set_tags("Japan")
    )
    assert q_py == q


def test_reader_singlechoice_multiple_correct_rejected(tmp_path):
    from questionsafe import Reader

    md_text = textwrap.dedent(
        """
        ---
        type: singlechoice
        name: bad
        choices:
          correct: [A, B]
          wrong: [C]
        ---

        Body
        """
    ).strip()
    p = tmp_path / "bad.md"
    p.write_text(md_text, encoding="utf-8")

    import pytest
    with pytest.raises(ValueError) as excinfo:
        Reader(p).read()
    assert "expects exactly one correct" in str(excinfo.value)
