# Moodle version capability table.
#
# Maps question types (by qtype slug) and per-question features to the first
# Moodle version whose XML importer understands them. Everything questionsafe
# emits today predates any version worth targeting, so only genuinely
# version-gated entries appear here; absence means "always available".
#
# Sources are verified against question/format/xml/format.php on Moodle's
# stable branches (see docs/references.md). When adding a type or feature,
# verify the minimum version the same way; do not guess.
from __future__ import annotations

import re
from typing import Any, Iterable, List, Tuple

Version = Tuple[int, int]

# qtype slug -> minimum Moodle version. Populate when a version-gated type
# lands (e.g., "ordering" is core only since 4.5).
TYPE_MIN_VERSION: dict[str, Version] = {}

# per-question feature -> minimum Moodle version
FEATURE_MIN_VERSION: dict[str, Version] = {
    # <idnumber> absent from format.php through MOODLE_35_STABLE, present in 3.6
    "idnumber": (3, 6),
}

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)$")


def parse_version(s: str) -> Version:
    """Parse a Moodle version string like "4.5" into a (major, minor) tuple."""
    m = _VERSION_RE.match(s.strip())
    if not m:
        raise ValueError(f"Invalid Moodle version {s!r}; expected 'MAJOR.MINOR' like '4.5'")
    return (int(m.group(1)), int(m.group(2)))


def _fmt(v: Version) -> str:
    return f"{v[0]}.{v[1]}"


def check_target(questions: Iterable[Any], target: str) -> List[str]:
    """Check questions against a target Moodle version.

    Accepts any iterable of questions (a Quiz iterates its items); Category
    nodes and other items without a qtype are skipped. Returns one message per
    problem found; an empty list means the quiz fits the target.
    """
    t = parse_version(target)
    msgs: List[str] = []
    for q in questions:
        qtype = getattr(q, "qtype", None)
        if qtype is None:
            continue
        name = getattr(q, "name", "?")
        req = TYPE_MIN_VERSION.get(qtype)
        if req is not None and t < req:
            msgs.append(
                f"{name}: question type '{qtype}' requires Moodle >= {_fmt(req)} (target {_fmt(t)})"
            )
        if getattr(q, "idnumber", None) and t < FEATURE_MIN_VERSION["idnumber"]:
            msgs.append(
                f"{name}: idnumber requires Moodle >= {_fmt(FEATURE_MIN_VERSION['idnumber'])} (target {_fmt(t)})"
            )
    return msgs
