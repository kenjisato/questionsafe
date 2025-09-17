import os
from pathlib import Path
from typer.testing import CliRunner

from questionsafe.cli import app


def test_init_scaffolds_project(tmp_path: Path):
    runner = CliRunner()
    res = runner.invoke(app, ["init", str(tmp_path)])
    assert res.exit_code == 0, res.output

    # Check directories and files
    assert (tmp_path / "questions").exists()
    assert (tmp_path / "templates").exists()
    cfg = tmp_path / "questionsafe.yml"
    assert cfg.exists()
    text = cfg.read_text(encoding="utf-8")
    assert "project:" in text and "questions:" in text and "templates:" in text

    # At least one template copied
    templates = list((tmp_path / "templates").glob("*.md.j2"))
    assert templates, "No templates copied"


def test_create_resolves_relative_to_questions_root(tmp_path: Path):
    # Initialize to create config and templates
    runner = CliRunner()
    res = runner.invoke(app, ["init", str(tmp_path)])
    assert res.exit_code == 0

    # Now create without absolute path; should resolve under project.questions
    q_rel = "unit/test.md"

    # Change CWD to the project root so CLI discovers questionsafe.yml
    cwd_saved = os.getcwd()
    try:
        os.chdir(tmp_path)
        res2 = runner.invoke(
            app,
            [
                "create",
                q_rel,
                "--name",
                "Project/Scoped",
                "--type",
                "singlechoice",
            ],
            env={"PYTHONPATH": str((Path(__file__).resolve().parents[1] / "src").resolve())},
        )
    finally:
        os.chdir(cwd_saved)
    assert res2.exit_code == 0, res2.output
    # The output path should be under questions root
    out_path = tmp_path / "questions" / q_rel
    assert out_path.exists(), f"Expected at {out_path}, got missing"

