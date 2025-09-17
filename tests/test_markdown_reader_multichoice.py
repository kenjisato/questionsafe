from __future__ import annotations
import math
import textwrap


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


essay_body = """
Pick EU capitals
"""


def test_reader_multichoice_choices(tmp_path):
    from questionsafe import Reader, Q, Text

    p = _write(
        tmp_path,
        """
        ---
        type: multichoice
        name: Capitals/EU
        choices:
          correct: [Paris, Berlin]
          wrong: [Madrid, Zurich]
        tags: [EU]
        choice_layout:
          labels: ABCD
          shuffle: false
          single_choice: false
        ---

        Pick EU capitals
        """,
    )

    q = Reader(p).read()
    assert isinstance(q, Q.MultiChoice)
    assert q.name == "Capitals/EU"
    # question text treated as markdown by default
    assert q.questiontext.format == "markdown"
    assert "Pick EU capitals" in q.questiontext.text

    positives = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) > 0]
    wrongs = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) <= 0]

    # Two correct, uniform distribution to sum to 100
    assert len(positives) == 2
    assert {a.text.strip() for a in positives} == {"Paris", "Berlin"}
    assert math.isclose(sum(float(a.fraction) for a in positives), 100.0, rel_tol=1e-6, abs_tol=1e-6)
    for a in positives:
        assert math.isclose(float(a.fraction), 50.0, rel_tol=1e-6, abs_tol=1e-6)

    # Wrong answers present
    assert {a.text.strip() for a in wrongs} >= {"Madrid", "Zurich"}

    # Options carried over
    assert getattr(q, "labels", None) == "ABCD"
    assert getattr(q, "shuffle", None) is False
    assert getattr(q, "single_choice", None) is False

    assert q.tags == ["EU"]

    # Assert semantic equivalence with Python API
    q_py = (
        Q.MultiChoice(name="Capitals/EU")
        .ask(Text("Pick EU capitals", format="markdown"))
        .set_choices_correct("Paris", "Berlin")
        .set_choices_wrong("Madrid", "Zurich")
        .set_labels("ABCD")
        .set_shuffle(False)
        .set_tags("EU")
    )
    assert q_py == q

