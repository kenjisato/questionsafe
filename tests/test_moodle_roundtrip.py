"""Round-trip test against a real Moodle in a Podman container.

Moodle's importer is the oracle for the XML we emit (docs/roadmap.md, section A):
import our XML into a containerized Moodle, export it back with qformat_xml,
and compare what survived.

Opt-in because it needs a running container stack (several minutes on first start):

    scripts/moodle/moodle-rt.sh up
    QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py -v
    scripts/moodle/moodle-rt.sh down
"""
from __future__ import annotations

import os
import re
import subprocess
import textwrap
from collections import Counter
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("QS_MOODLE_ROUNDTRIP"),
    reason="needs a containerized Moodle: scripts/moodle/moodle-rt.sh up, then QS_MOODLE_ROUNDTRIP=1",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER = "qsafe-moodle-web"
HARNESS = REPO_ROOT / "scripts" / "moodle" / "roundtrip.php"


# --- container plumbing -------------------------------------------------------

def _podman(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["podman", *args], capture_output=True, text=True, **kwargs)


def _roundtrip(xml: bytes, tmp_path: Path) -> tuple[bytes, str]:
    """Import xml into the container's Moodle, export it back.

    Returns (exported_xml, moodle_release).
    """
    import_file = tmp_path / "import.xml"
    import_file.write_bytes(xml)
    for src, dst in [
        (str(HARNESS), f"{CONTAINER}:/tmp/roundtrip.php"),
        (str(import_file), f"{CONTAINER}:/tmp/import.xml"),
    ]:
        cp = _podman("cp", src, dst)
        assert cp.returncode == 0, f"podman cp failed: {cp.stderr}"

    run = _podman(
        "exec", CONTAINER,
        "php", "/tmp/roundtrip.php", "/tmp/import.xml", "/tmp/export.xml",
    )
    assert run.returncode == 0, (
        f"harness failed\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    release = ""
    m = re.search(r"MOODLE_RELEASE=(.+)", run.stdout)
    if m:
        release = m.group(1).strip()

    export_file = tmp_path / "export.xml"
    cp = _podman("cp", f"{CONTAINER}:/tmp/export.xml", str(export_file))
    assert cp.returncode == 0, f"podman cp back failed: {cp.stderr}"
    return export_file.read_bytes(), release


# --- XML comparison -----------------------------------------------------------

def _norm(s: str | None) -> str:
    return " ".join((s or "").split())


def _fingerprints(xml: bytes) -> Counter:
    """Reduce a quiz XML to a multiset of comparable question fingerprints.

    Strict for the answer-bearing types (texts + fractions + tolerances must
    survive); presence-level for essay/description/multianswer.
    """
    from lxml import etree

    root = etree.fromstring(xml)
    out: Counter = Counter()
    for q in root.findall("question"):
        qtype = q.get("type")
        if qtype in (None, "category"):
            continue
        name = _norm(q.findtext("name/text"))
        qtext = _norm(q.findtext("questiontext/text"))
        if qtype == "numerical":
            answers = frozenset(
                (
                    round(float(_norm(a.findtext("text"))), 6),
                    round(float(a.get("fraction")), 5),
                    round(float(_norm(a.findtext("tolerance")) or 0), 6),
                )
                for a in q.findall("answer")
            )
            units = frozenset(_norm(u.findtext("unit_name")) for u in q.findall(".//units/unit"))
            out[(qtype, name, qtext, answers, units)] += 1
        elif qtype in ("multichoice", "truefalse", "shortanswer"):
            answers = frozenset(
                (_norm(a.findtext("text")), round(float(a.get("fraction")), 5))
                for a in q.findall("answer")
            )
            out[(qtype, name, qtext, answers, frozenset())] += 1
        else:
            # essay, description, multianswer (cloze): reimport reconstructs the
            # body from parsed parts, so compare only identity here.
            out[(qtype, name, "", frozenset(), frozenset())] += 1
    return out


# --- quiz under test ----------------------------------------------------------

def _write(tmp_path: Path, rel: str, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def _build_quiz(tmp_path: Path):
    """One question per type, plus the metachoice example's generated variants."""
    from questionsafe import Q, Quiz, Reader, Text

    qz = Quiz(category="RT")

    mc = (
        Q.MultiChoice(name="rt-multichoice")
        .set_questiontext(Text("Which are *prime*?", format="markdown"))
        .set_choices_correct("2", "3", "5")  # 3-way split: snapped 33.33333 each
        .set_choices_wrong("4", "6")
    )
    sc = (
        Q.SingleChoice(name="rt-singlechoice")
        .set_questiontext("Capital of Japan?")
        .set_choice_correct("Tokyo")
        .set_choices_wrong("Osaka", "Kyoto")
    )
    tf = (
        Q.TrueFalse(name="rt-truefalse")
        .set_questiontext("1 + 1 == 2")
        .set_correct_if_true()
    )
    sa = (
        Q.ShortAnswer(name="rt-shortanswer")
        .set_questiontext("Name a primary color.")
        .add_answer("red")
        .add_answer("blue", fraction=50.0)
    )
    from questionsafe.base import Unit

    num = (
        Q.Numerical(name="rt-numerical")
        .set_questiontext("Speed after 2 s at 9.8 m/s^2?")
        .add_answer(19.6, 0.1)
        .add_units(Unit("m/s", 1.0))
    )
    essay = (
        Q.Essay(name="rt-essay")
        .set_questiontext("Discuss comparative advantage.")
    )
    desc = (
        Q.Description(name="rt-description")
        .set_questiontext("The following questions concern the coffee market.")
    )

    _write(
        tmp_path,
        "gap.md",
        """
        ---
        type: singlechoice
        name: gap1
        choices:
          correct: [Tokyo]
          wrong: [Osaka, Kyoto]
        ---


        """,
    )
    cloze_path = _write(
        tmp_path,
        "cloze.md",
        """
        ---
        type: cloze
        name: rt-cloze
        cloze:
          gap1: gap.md
        ---

        The capital of Japan is {{gap1}}.
        """,
    )
    cloze = Reader(cloze_path).read()

    for q in (mc, sc, tf, sa, num, essay, desc, cloze):
        qz.add(q)

    meta = Reader(REPO_ROOT / "examples" / "markdown" / "metachoice.md").read_metachoice()
    qz.add_group(meta.generate_multichoice(n=4, limit=2, seed=42))
    return qz


# --- the test -----------------------------------------------------------------

def test_roundtrip_through_real_moodle(tmp_path):
    from questionsafe.writer.moodle import render_xml

    qz = _build_quiz(tmp_path)
    ours = render_xml(qz)

    theirs, release = _roundtrip(ours, tmp_path)
    assert release, "harness did not report the Moodle release"
    print(f"\nround-tripped against Moodle {release}")

    ours_fp = _fingerprints(ours)
    theirs_fp = _fingerprints(theirs)

    missing = ours_fp - theirs_fp
    extra = theirs_fp - ours_fp
    assert not missing and not extra, (
        f"round-trip mismatch against Moodle {release}\n"
        f"missing after reimport: {sorted(missing)}\n"
        f"unexpected after reimport: {sorted(extra)}"
    )
