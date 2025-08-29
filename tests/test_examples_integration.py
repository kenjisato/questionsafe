import os
import sys
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
EXAMPLES_DIR = REPO_ROOT / "examples"


def run_example(script: Path, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Ensure our in-repo package can be imported
    env["PYTHONPATH"] = str(SRC_DIR)
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(cwd or REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "script, expected_snippets",
    [
        ("singlechoice.py", ["<quiz>", '<question type="multichoice">', "</quiz>"]),
        ("multichoice.py", ["<quiz>", '<question type="multichoice">', "</quiz>"]),
        ("truefalse.py", ["<quiz>", '<question type="truefalse">', "</quiz>"]),
        ("shortanswer.py", ["<quiz>", '<question type="shortanswer">', "</quiz>"]),
        ("numerical.py", ["<quiz>", '<question type="numerical">', "</quiz>"]),
        ("essay.py", ["<quiz>", '<question type="essay">', "</quiz>"]),
        ("description.py", ["<quiz>", '<question type="description">', "</quiz>"]),
    ],
)
def test_examples_emit_xml_stdout(script: str, expected_snippets: list[str]):
    script_path = EXAMPLES_DIR / script
    proc = run_example(script_path)
    assert proc.returncode == 0, f"{script} failed: stderr=\n{proc.stderr}"
    out = proc.stdout
    assert out.strip(), f"{script} produced no stdout"
    for snippet in expected_snippets:
        assert snippet in out, (
            f"{script} missing snippet: {snippet}\nOutput was:\n{out}"
        )

    # Extended checks per script
    if script in ("singlechoice.py", "multichoice.py"):
        # questiontext format present and answer format set to html
        assert '<questiontext format="html">' in out
        assert '<answer fraction="' in out and 'format="html"' in out
        # idnumber should be empty for single examples
        assert "<idnumber></idnumber>" in out
    elif script == "truefalse.py":
        assert '<question type="truefalse">' in out
        assert "<idnumber></idnumber>" in out
    elif script == "shortanswer.py":
        assert 'format="moodle_auto_format"' in out
        assert "<idnumber></idnumber>" in out
    elif script == "numerical.py":
        assert 'format="moodle_auto_format"' in out
        assert "<idnumber></idnumber>" in out
    elif script == "essay.py":
        assert '<graderinfo format="' in out
        assert "<idnumber></idnumber>" in out
    elif script == "description.py":
        assert '<questiontext format="html">' in out
        assert "<idnumber></idnumber>" in out


def test_combined_writes_files(tmp_path: Path):
    script_path = EXAMPLES_DIR / "combined.py"
    proc = run_example(script_path, cwd=tmp_path)
    assert proc.returncode == 0, f"combined.py failed: stderr=\n{proc.stderr}"

    # Check files were written
    xml_path = tmp_path / "build" / "combined.xml"
    html_path = tmp_path / "build" / "combined.html"
    assert xml_path.exists(), "combined.xml not written"
    assert html_path.exists(), "combined.html not written"

    xml = xml_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")

    # Basic sanity checks on XML and HTML outputs
    assert "<quiz>" in xml and "</quiz>" in xml
    # Expect at least these question types to appear in the XML
    for qtype in (
        "multichoice",
        "truefalse",
        "shortanswer",
        "numerical",
        "essay",
        "description",
    ):
        assert f'<question type="{qtype}">' in xml

    # Ensure categories inserted by add_group exist
    assert '<question type="category">' in xml
    assert "<category>" in xml

    # Check idnumbers exist for grouped questions with prefixes
    for prefix in ("mcq-", "tf-", "sa-", "num-", "essay-", "desc-"):
        assert f"<idnumber>{prefix}" in xml

    assert "<html" in html.lower() and "</html>" in html.lower()
