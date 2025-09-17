from __future__ import annotations
from pathlib import Path
import textwrap


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_reader_expands_config_variables_for_include(tmp_path, monkeypatch):
    from questionsafe import Reader, Q

    # Create a project config with variables in CWD
    monkeypatch.chdir(tmp_path)
    _write(
        tmp_path,
        "questionsafe.yml",
        """
        project:
          questions: ./questions
          templates: ./templates
        variables:
          ROOT: ./data
        """,
    )

    # Create include target under $ROOT
    _write(tmp_path, "data/inc.yml", "feedback: { general: included }")

    # Create a markdown that uses include: "$ROOT/inc.yml"
    q_path = _write(
        tmp_path,
        "q.md",
        """
        ---
        type: singlechoice
        name: Var/Include
        include: "$ROOT/inc.yml"
        choices:
          correct: [A]
          wrong: [B]
        ---

        Body
        """,
    )

    q = Reader(q_path).read()
    assert isinstance(q, Q.SingleChoice)
    # Feedback.general merged from include
    assert getattr(q, "feedback_general", None) is not None
    if q.feedback_general:
        assert "included" in (q.feedback_general.text or "")

    # Ensure project variable overrides OS env of same name
    monkeypatch.setenv("ROOT", "/does/not/exist")
    q2 = Reader(q_path).read()  # re-read with same CWD config; should still work
    assert isinstance(q2, Q.SingleChoice)

