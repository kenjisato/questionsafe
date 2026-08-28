from __future__ import annotations
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from questionsafe.cli import app


runner = CliRunner()

VALID_TF = """
---
type: truefalse
name: TF/Valid
answer: true
---

1 + 1 == 2
"""

VALID_TF_WITH_ID = """
---
type: truefalse
name: TF/WithId
answer: true
id: q-001
---

2 + 2 == 4
"""

INVALID_MC = """
---
type: multichoice
name: MC/Bad
answers:
  - text: Alpha
    fraction: 50
  - text: Beta
    fraction: 30
---

Pick some.
"""


VALID_METACHOICE = """
---
type: metachoice
name: Mini/Meta
choices:
  C1: Correct one
  C2: Correct two
  D1: Wrong one
  D2: Wrong two
stems:
  Q1: Pick one
---

```csv
choice,Q1
C1,x
C2,x
D1,
D2,-
```
"""

INVALID_METACHOICE = VALID_METACHOICE.replace("C1,x", "NOPE,x")


def _write(dir: Path, rel: str, text: str) -> Path:
    p = dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_validate_ok_single_file(tmp_path: Path):
    p = _write(tmp_path, "ok.md", VALID_TF)
    res = runner.invoke(app, ["validate", str(p)])
    assert res.exit_code == 0
    assert "1 file" in res.output
    assert "OK" in res.output


def test_validate_invalid_file_fails_and_names_file(tmp_path: Path):
    p = _write(tmp_path, "bad.md", INVALID_MC)
    res = runner.invoke(app, ["validate", str(p)])
    assert res.exit_code == 1
    assert "bad.md" in res.output


def test_validate_directory_recurses_and_counts(tmp_path: Path):
    _write(tmp_path, "a/ok.md", VALID_TF)
    _write(tmp_path, "a/b/bad.md", INVALID_MC)
    res = runner.invoke(app, ["validate", str(tmp_path)])
    assert res.exit_code == 1
    assert "2 files" in res.output
    assert "bad.md" in res.output


def test_validate_metachoice_template_ok(tmp_path: Path):
    p = _write(tmp_path, "meta.md", VALID_METACHOICE)
    res = runner.invoke(app, ["validate", str(p)])
    assert res.exit_code == 0
    assert "OK" in res.output
    assert "metachoice template" in res.output


def test_validate_metachoice_error_names_key(tmp_path: Path):
    p = _write(tmp_path, "meta.md", INVALID_METACHOICE)
    res = runner.invoke(app, ["validate", str(p)])
    assert res.exit_code == 1
    assert "NOPE" in res.output


def test_validate_directory_mixing_metachoice_counts_both(tmp_path: Path):
    _write(tmp_path, "a/tf.md", VALID_TF)
    _write(tmp_path, "a/meta.md", VALID_METACHOICE)
    res = runner.invoke(app, ["validate", str(tmp_path)])
    assert res.exit_code == 0
    assert "2 files" in res.output


def test_validate_target_flags_idnumber(tmp_path: Path):
    p = _write(tmp_path, "with_id.md", VALID_TF_WITH_ID)
    res = runner.invoke(app, ["validate", str(p), "--target", "3.5"])
    assert res.exit_code == 1
    assert "idnumber" in res.output

    res_ok = runner.invoke(app, ["validate", str(p), "--target", "4.5"])
    assert res_ok.exit_code == 0


def test_validate_rejects_bad_target(tmp_path: Path):
    p = _write(tmp_path, "ok.md", VALID_TF)
    res = runner.invoke(app, ["validate", str(p), "--target", "banana"])
    assert res.exit_code != 0


def test_validate_missing_path_fails(tmp_path: Path):
    res = runner.invoke(app, ["validate", str(tmp_path / "nope.md")])
    assert res.exit_code == 1
