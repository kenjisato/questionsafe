"""Round-trip test against a real Moodle in a Podman container.

Moodle's importer is the oracle for the XML we emit (docs/roadmap.md, section A):
import our XML into a containerized Moodle, export it back with qformat_xml,
and compare what survived.

Opt-in because it needs a running container stack (several minutes on first start):

    scripts/moodle/moodle-rt.sh up 405; scripts/moodle/moodle-rt.sh up 502
    QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py -v
    scripts/moodle/moodle-rt.sh down

Every test runs once per running stack (qsafe-moodle-BRANCH-web).
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
HARNESS = REPO_ROOT / "scripts" / "moodle" / "roundtrip.php"
FORMAT_HARNESS = REPO_ROOT / "scripts" / "moodle" / "format_text.php"


# --- container plumbing -------------------------------------------------------

def _podman(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["podman", *args], capture_output=True, text=True, **kwargs)


def _running_stacks() -> list[str]:
    if not os.environ.get("QS_MOODLE_ROUNDTRIP"):
        return []
    ps = _podman("ps", "--format", "{{.Names}}")
    return sorted(n for n in ps.stdout.split() if re.fullmatch(r"qsafe-moodle-\d+-web", n))


@pytest.fixture(params=_running_stacks() or [None])
def container(request) -> str:
    if request.param is None:
        pytest.fail("no Moodle stack is running: scripts/moodle/moodle-rt.sh up [BRANCH]")
    return request.param


def _roundtrip(xml: bytes, tmp_path: Path, container: str) -> tuple[bytes, str]:
    """Import xml into the container's Moodle, export it back.

    Returns (exported_xml, moodle_release).
    """
    import_file = tmp_path / "import.xml"
    import_file.write_bytes(xml)
    for src, dst in [
        (str(HARNESS), f"{container}:/tmp/roundtrip.php"),
        (str(import_file), f"{container}:/tmp/import.xml"),
    ]:
        cp = _podman("cp", src, dst)
        assert cp.returncode == 0, f"podman cp failed: {cp.stderr}"

    run = _podman(
        "exec", container,
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
    cp = _podman("cp", f"{container}:/tmp/export.xml", str(export_file))
    assert cp.returncode == 0, f"podman cp back failed: {cp.stderr}"
    return export_file.read_bytes(), release


def _format_text(items: list[dict], tmp_path: Path, container: str) -> list[str]:
    """Render [{text, format}] with Moodle's format_text(), as a student would see it."""
    import json

    infile = tmp_path / "format_in.json"
    infile.write_text(json.dumps(items), encoding="utf-8")
    for src, dst in [
        (str(FORMAT_HARNESS), f"{container}:/tmp/format_text.php"),
        (str(infile), f"{container}:/tmp/format_in.json"),
    ]:
        cp = _podman("cp", src, dst)
        assert cp.returncode == 0, f"podman cp failed: {cp.stderr}"
    run = _podman("exec", container, "php", "/tmp/format_text.php", "/tmp/format_in.json", "/tmp/format_out.json")
    assert run.returncode == 0, f"format harness failed\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    outfile = tmp_path / "format_out.json"
    cp = _podman("cp", f"{container}:/tmp/format_out.json", str(outfile))
    assert cp.returncode == 0, f"podman cp back failed: {cp.stderr}"
    return json.loads(outfile.read_text(encoding="utf-8"))


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
            units = frozenset(
                (_norm(u.findtext("unit_name")), round(float(u.findtext("multiplier")), 6))
                for u in q.findall(".//units/unit")
            ) | {
                (k, round(float(q.findtext(k) or 0), 5))
                for k in ("showunits", "unitgradingtype", "unitpenalty", "unitsleft")
            }
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
        .add_units(Unit("m/s"), Unit("km/h", 3.6), handling="graded", input="select", penalty=0.3)
    )
    num_units = (
        Q.Numerical(name="rt-numerical-units")
        .set_questiontext("100 g + 1 kg?")
        .add_answer_unit(1100, "g")
        .add_answer_unit(1.1, "kg")
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

    for q in (mc, sc, tf, sa, num, num_units, essay, desc, cloze):
        qz.add(q)

    meta = Reader(REPO_ROOT / "examples" / "markdown" / "metachoice.md").read_metachoice()
    qz.add_group(meta.generate_multichoice(n=4, limit=2, seed=42))
    return qz


# --- the test -----------------------------------------------------------------

def test_roundtrip_through_real_moodle(tmp_path, container):
    from questionsafe.writer.moodle import render_xml

    qz = _build_quiz(tmp_path)
    ours = render_xml(qz)

    theirs, release = _roundtrip(ours, tmp_path, container)
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


MATH = [
    r"\( a*b*c + x_1 + y_2 \)",
    r"\( \{x : x > 0\} \)",
    r"\( \frac{\partial Y}{\partial K} = \alpha \)",
    r"\[ \begin{aligned} a &= b \\ c &= d \end{aligned} \]",
]


def test_markdown_math_reaches_the_student(tmp_path, container):
    """TeX in markdown texts survives import and Moodle's Markdown rendering (#7)."""
    import html

    from lxml import etree

    from questionsafe import Q, Quiz, Text
    from questionsafe.base import Feedback
    from questionsafe.writer.moodle import render_xml

    body = "Let " + " and ".join(MATH) + ", with *emphasis*."
    sc = (
        Q.SingleChoice(name="rt-math-sc")
        .set_questiontext(Text(body, format="markdown"))
        .set_choice_correct("A")
        .set_choices_wrong("B")
    )
    sc.set_feedback_general(Feedback(body, format="markdown"))
    gap = Q.SingleChoice(name="g").set_choice_correct("Tokyo").set_choices_wrong("Osaka")
    cloze = Q.Cloze(name="rt-math-cloze", questiontext=Text(body + " {{g}}", format="markdown"))
    cloze.embed_question(gap)
    qz = Quiz(category="RT-math")
    qz.add(sc)
    qz.add(cloze)

    theirs, release = _roundtrip(render_xml(qz), tmp_path, container)
    root = etree.fromstring(theirs)
    fields = [
        (q.findtext("name/text").strip(), tag, el.get("format"), el.findtext("text"))
        for q in root.findall("question")
        if q.get("type") != "category"
        for tag in ("questiontext", "generalfeedback")
        if (el := q.find(tag)) is not None and el.findtext("text")
    ]
    assert {(n, t) for n, t, _, _ in fields} >= {
        ("rt-math-sc", "questiontext"),
        ("rt-math-sc", "generalfeedback"),
        ("rt-math-cloze", "questiontext"),
    }
    rendered = _format_text([{"text": text, "format": fmt} for _, _, fmt, text in fields], tmp_path, container)
    for (name, tag, fmt, _), out in zip(fields, rendered):
        shown = _norm(html.unescape(re.sub(r"<[^>]+>", "", out)))
        for tex in MATH:
            assert _norm(tex) in shown, f"{name}/{tag} ({fmt}) on Moodle {release}: {tex!r} not in {shown!r}"
        assert "<em>emphasis</em>" in out


def test_markdown_choices_reach_the_student(tmp_path, container):
    """Choices and their feedback keep format: markdown through import (#8)."""
    from lxml import etree

    from questionsafe import Q, Quiz, Text
    from questionsafe.writer.moodle import render_xml

    md = r"**bold** \( a*b \)"
    q = (
        Q.MultiChoice(name="rt-md-choices")
        .set_questiontext(Text("Pick.", format="markdown"))
        .set_choices_correct(Text(md, format="markdown"), feedback=Text(md, format="markdown"))
        .set_choices_wrong("B")
    )
    qz = Quiz(category="RT-md-choices")
    qz.add(q)

    theirs, release = _roundtrip(render_xml(qz), tmp_path, container)
    (answer,) = [
        a for a in etree.fromstring(theirs).iterfind("question/answer") if a.get("fraction") == "100"
    ]
    fields = [(answer.get("format"), answer.findtext("text")), (answer.find("feedback").get("format"), answer.findtext("feedback/text"))]
    assert [fmt for fmt, _ in fields] == ["markdown", "markdown"], f"on Moodle {release}"
    for out in _format_text([{"text": t, "format": f} for f, t in fields], tmp_path, container):
        assert "<strong>bold</strong>" in out and r"\( a*b \)" in out, f"on Moodle {release}: {out!r}"


def test_essay_template_reaches_the_student_as_written(tmp_path, container):
    """Moodle pre-fills the answer box with the template text, unformatted."""
    from lxml import etree

    from questionsafe import Q, Quiz, Text
    from questionsafe.writer.moodle import render_xml

    md = r"Intro: **fill** \( a*b \)"
    q = Q.Essay(name="rt-essay-tpl", questiontext="Explain.").set_response_template(Text(md, format="markdown"))
    qz = Quiz(category="RT-essay-tpl")
    qz.add(q)

    theirs, release = _roundtrip(render_xml(qz), tmp_path, container)
    el = etree.fromstring(theirs).find("question[@type='essay']/responsetemplate")
    assert (el.get("format"), el.findtext("text")) == ("markdown", md), f"on Moodle {release}"


def test_images_survive_import(tmp_path, container):
    """Embedded images in question text and choices come back under their hashed names (#3)."""
    import base64

    from lxml import etree

    from questionsafe import Q, Quiz, Text
    from questionsafe.writer.moodle import render_xml

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    for name, salt in [("stem.png", b""), ("correct.png", b"C"), ("wrong.png", b"W")]:
        (tmp_path / name).write_bytes(png + salt)
    q = (
        Q.SingleChoice(name="rt-images")
        .set_questiontext(Text(f"Which? ![The figure]({tmp_path / 'stem.png'})", format="markdown"))
        .set_choice_correct(Text(f"![correct]({tmp_path / 'correct.png'})", format="markdown"))
        .set_choices_wrong(f'<img src="{tmp_path / "wrong.png"}" alt="wrong">')
    )
    qz = Quiz(category="RT-images")
    qz.add(q)
    ours = render_xml(qz)

    def files(xml: bytes) -> list[tuple[str, dict[str, bytes]]]:
        (el,) = etree.fromstring(xml).findall("question[@type='multichoice']")
        return [
            (f.findtext("text"), {x.get("name"): base64.b64decode(x.text) for x in f.findall("file")})
            for f in [el.find("questiontext"), *el.findall("answer")]
        ]

    theirs, release = _roundtrip(ours, tmp_path, container)
    assert sorted(files(theirs)) == sorted(files(ours)), f"on Moodle {release}"
    assert all(f for _, f in files(theirs))


def test_single_choice_partial_credit_survives_import(tmp_path, container):
    """A single-answer multichoice may give partial credit besides the 100% answer (#13)."""
    from lxml import etree

    from questionsafe import Answer, Q, Quiz
    from questionsafe.writer.moodle import render_xml

    q = Q.MultiChoice(name="rt-single-partial", questiontext="Pick.").set_single_choice().set_shuffle(False)
    for t, f in [("A", 100), ("B", 50), ("C", 0)]:
        q.add_answer(Answer.from_text(t, fraction=f))
    qz = Quiz(category="RT-single-partial")
    qz.add(q)

    theirs, release = _roundtrip(render_xml(qz), tmp_path, container)
    el = etree.fromstring(theirs).find("question[@type='multichoice']")
    assert el.findtext("single") == "true", f"on Moodle {release}"
    fractions = sorted(float(a.get("fraction")) for a in el.findall("answer"))
    assert fractions == [0.0, 50.0, 100.0], f"on Moodle {release}"
