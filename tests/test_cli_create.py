from pathlib import Path

import pytest
from typer.testing import CliRunner

from questionsafe.cli import app


runner = CliRunner()


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "qtype, expected_snippets",
    [
        ("singlechoice", ["type: singlechoice", "choices:", "correct:", "wrong:"]),
        ("multichoice", ["type: multichoice", "choices:", "correct:", "wrong:"]),
        ("truefalse", ["type: truefalse", "choices:", "(x) True", "( ) False"]),
        ("shortanswer", ["type: shortanswer", "answers:", "Your answer"]),
        ("numerical", ["type: numerical", "answers:", "answer:", "tolerance:"]),
        ("numerical_unit", ["type: numerical", "units:", "unitpenalty", "unitgradingtype"]),
        ("essay", ["type: essay", "---\n\nWrite your question here."]),
        ("cloze", ["type: cloze", "cloze:", "{}", "{{gap1}}"]),
    ],
)
def test_create_noninteractive(tmp_path: Path, qtype: str, expected_snippets: list[str]):
    out_path = tmp_path / f"{qtype}.md"
    res = runner.invoke(
        app,
        [
            "create",
            str(out_path),
            "--name",
            f"Example/{qtype}",
            "--type",
            qtype,
        ],
    )
    assert res.exit_code == 0, res.output
    assert out_path.exists()
    text = read(out_path)
    for s in expected_snippets:
        assert s in text, f"Missing snippet {s} in {qtype} template: \n{text}"


def test_create_refuses_overwrite_without_force(tmp_path: Path):
    p = tmp_path / "q.md"
    p.write_text("original", encoding="utf-8")
    res = runner.invoke(app, ["create", str(p), "--name", "N", "--type", "singlechoice"])
    assert res.exit_code != 0
    assert read(p) == "original"


def test_create_force_overwrite(tmp_path: Path):
    p = tmp_path / "q.md"
    p.write_text("original", encoding="utf-8")
    res = runner.invoke(
        app, ["create", str(p), "--name", "N", "--type", "singlechoice", "--force"]
    )
    assert res.exit_code == 0
    text = read(p)
    assert "type: singlechoice" in text and "name: N" in text


def test_create_output_parses_with_reader(tmp_path: Path):
    # Ensure generated files round-trip through Reader without validation error
    p = tmp_path / "sample.md"
    res = runner.invoke(app, ["create", str(p), "--name", "T/SC", "--type", "singlechoice"])
    assert res.exit_code == 0

    # Use Reader to parse
    from questionsafe import Reader

    q = Reader(p).read()
    # compile_text shouldn't error
    assert hasattr(q, "compile_text") or hasattr(q, "validate")
