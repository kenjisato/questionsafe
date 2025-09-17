from __future__ import annotations
import textwrap
import pytest


from questionsafe import Reader, Q, render_xml


def test_reader_include_yaml_singlechoice(tmp_path):
    md = textwrap.dedent(
        """
        ---
        name: Japan/Capital
        type: singlechoice
        include: question.yml
        ---

        What is the capital of Japan?
        """
    ).strip()
    yml = textwrap.dedent(
        """
        answers:
          - text: Tokyo
            fraction: 100
            feedback:
              text: Right!
              format: html
          - text: Osaka
            fraction: 0
        feedback:
          general:
            text: GF here
            format: markdown
        """
    ).strip()
    md_path = tmp_path / "q.md"
    yml_path = tmp_path / "question.yml"
    md_path.write_text(md, encoding="utf-8")
    yml_path.write_text(yml, encoding="utf-8")

    q = Reader(md_path).read()
    assert isinstance(q, Q.SingleChoice)
    assert q.name == "Japan/Capital"
    # Answers merged from YAML
    positives = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) > 0]
    assert len(positives) == 1 and positives[0].text.strip() == "Tokyo"
    wrongs = [a for a in q.answers if float(getattr(a, "fraction", 0.0)) <= 0]
    assert any(a.text.strip() == "Osaka" for a in wrongs)

    # General feedback merged
    xml = render_xml([q]).decode("utf-8")
    assert '<generalfeedback format="markdown">' in xml
    assert 'GF here' in xml


def test_reader_include_conflict_outer_wins(tmp_path):
    md = textwrap.dedent(
        """
        ---
        name: F
        type: singlechoice
        include: q.yml
        answers:
          - text: A
            fraction: 100
        ---

        stem
        """
    ).strip()
    yml = textwrap.dedent(
        """
        answers:
          - text: B
            fraction: 100
        """
    ).strip()
    md_path = tmp_path / "q.md"
    yml_path = tmp_path / "q.yml"
    md_path.write_text(md, encoding="utf-8")
    yml_path.write_text(yml, encoding="utf-8")

    q = Reader(md_path).read()
    # outer front matter answer 'A' should win; ensure 'A' is present as the correct answer
    assert any(a.text.strip() == "A" and float(a.fraction) == 100.0 for a in q.answers)
    # and included conflicting value 'B' should not override
    assert not any(a.text.strip() == "B" and float(a.fraction) == 100.0 for a in q.answers)


def test_reader_include_conflict_emits_warning_when_opt_in(tmp_path):
    md = textwrap.dedent(
        """
        ---
        name: W
        type: singlechoice
        include: q.yml
        answers:
          - text: A
            fraction: 100
        ---

        stem
        """
    ).strip()
    yml = textwrap.dedent(
        """
        answers:
          - text: B
            fraction: 100
        """
    ).strip()
    md_path = tmp_path / "q.md"
    yml_path = tmp_path / "q.yml"

    md_path.write_text(md, encoding="utf-8")
    yml_path.write_text(yml, encoding="utf-8")

    with pytest.warns(UserWarning, match=r"Ignoring included value for key 'answers'"):
        q = Reader(md_path).read(include_warn=True)
    # Ensure precedence still correct
    assert any(a.text.strip() == "A" and float(a.fraction) == 100.0 for a in q.answers)
    assert not any(a.text.strip() == "B" and float(a.fraction) == 100.0 for a in q.answers)


def test_reader_include_from_qmd_metadata(tmp_path):
    md = textwrap.dedent(
        """
        ---
        name: FromQmd
        type: singlechoice
        include: inc.qmd
        ---

        stem from md
        """
    ).strip()
    qmd = textwrap.dedent(
        """
        ---
        answers:
          - text: Correct from qmd
            fraction: 100
          - text: Wrong from qmd
            fraction: 0
        feedback:
          general: gfb from qmd
        ---

        body is irrelevant
        """
    ).strip()
    md_path = tmp_path / "q.md"
    inc_path = tmp_path / "inc.qmd"
    md_path.write_text(md, encoding="utf-8")
    inc_path.write_text(qmd, encoding="utf-8")

    q = Reader(md_path).read()
    # merged answers from qmd front matter
    assert any(a.text.strip() == "Correct from qmd" and float(a.fraction) == 100.0 for a in q.answers)
    assert any(a.text.strip() == "Wrong from qmd" and float(a.fraction) == 0.0 for a in q.answers)


def test_reader_include_single_level_only(tmp_path):
    md = textwrap.dedent(
        """
        ---
        name: SingleLevel
        type: singlechoice
        include: inc.yml
        ---

        stem
        """
    ).strip()
    inc_yml = textwrap.dedent(
        """
        include: deeper.yml
        answers:
          - text: OuterIncluded
            fraction: 100
        """
    ).strip()
    deeper_yml = textwrap.dedent(
        """
        answers:
          - text: DeeperIncluded
            fraction: 100
        """
    ).strip()
    md_path = tmp_path / "q.md"
    inc_path = tmp_path / "inc.yml"
    deeper_path = tmp_path / "deeper.yml"
    md_path.write_text(md, encoding="utf-8")
    inc_path.write_text(inc_yml, encoding="utf-8")
    deeper_path.write_text(deeper_yml, encoding="utf-8")

    q = Reader(md_path).read()
    # Should include only from inc.yml, not from deeper.yml
    assert any(a.text.strip() == "OuterIncluded" and float(a.fraction) == 100.0 for a in q.answers)
    assert not any(a.text.strip() == "DeeperIncluded" for a in q.answers)

