import os
from pathlib import Path
from typer.testing import CliRunner

from questionsafe.cli import app


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_coverage_csv_course(tmp_path: Path):
    runner = CliRunner()

    # Scaffold base project
    res = runner.invoke(app, ["init", str(tmp_path)])
    assert res.exit_code == 0

    # Create some questions
    qroot = tmp_path / "questions"
    write(qroot / "unit1/q1.md", """
    ---
    type: truefalse
    name: Q1
    ---
    Body
    """.strip())
    write(qroot / "unit2/q3.md", """
    ---
    type: shortanswer
    name: Q3
    ---
    Body
    """.strip())

    # Create course CSVs
    cdir = tmp_path / "courses/ECON101"
    cdir.mkdir(parents=True, exist_ok=True)

    write(cdir / "topics.csv", "group,description\nA,General\nB,SNA\n")
    write(
        cdir / "objectives.csv",
        "group,index,description\n"
        "A,1,Can explain the purpose and targets of macroeconomics\n"
        "A,2,Can choose macroeconomic variables\n"
        "B,1,definition of GDP\n"
        "B,2,definition of implicit deflator\n",
    )
    write(
        cdir / "relationships.csv",
        "group,index,question,difficulty\n"
        "A,1,unit1/q1.md,1\n"
        "B,1,unit2/q3.md,2\n",
    )

    # Run coverage
    cwd_saved = os.getcwd()
    try:
        os.chdir(tmp_path)
        res2 = runner.invoke(app, ["course", "coverage", "ECON101"])
    finally:
        os.chdir(cwd_saved)

    assert res2.exit_code == 0, res2.output
    out = res2.stdout
    # Expect group summaries
    assert "A. General" in out
    assert "B. SNA" in out
    # Covered detail shows objective descriptions and question names
    assert "Can explain the purpose and targets of macroeconomics" in out and ("Q1" in out or "q1" in out)
    assert "definition of GDP" in out and ("Q3" in out or "q3" in out)
    # Uncovered should include A2 and B2
    assert "Uncovered Objectives" in out
    assert "A2" in out and "B2" in out

