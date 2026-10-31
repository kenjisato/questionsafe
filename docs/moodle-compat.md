---
title: "Moodle Compatibility"
page-layout: article
---

# Moodle Compatibility

Moodle publishes no XSD for its XML format, so questionsafe treats Moodle's own
importer (`qformat_xml`) as the oracle: the round-trip test imports our XML into
a containerized Moodle, exports it back, and compares what survived
(`tests/test_moodle_roundtrip.py`).

## Verified versions

| Moodle release | Result | Date | Scope |
|---|---|---|---|
| 5.2.4+ (Build: 20261030) | OK | 2026-10-31 | same round-trip test as below + markdown math display (`test_markdown_math_reaches_the_student`) |
| 4.5.15+ (Build: 20261030) | OK | 2026-10-31 | same round-trip test as below + markdown math display |
| 5.3+ (Build: 20261013) | OK | 2026-10-20 | same round-trip test as below |
| 5.2.4+ (Build: 20261013) | OK | 2026-10-20 | same round-trip test as below |
| 4.5.13+ (Build: 20260818) | OK | 2026-08-29 | multichoice (incl. 33.33333 fractions), singlechoice, truefalse, shortanswer, numerical (tolerance + unit), essay, description, cloze, MetaChoice-generated variants (14 questions) |

"OK" means: import with `matchgrades=error` and `stoponerror=1` succeeded, and
for the answer-bearing types the re-exported questions carried the same
question texts, answer texts, fractions, tolerances, and units. Essay,
description, and cloze are checked for identity (name + type) since Moodle
reconstructs their bodies from parsed parts.

## Running the round-trip test

Requires Podman (or Docker via `QS_CONTAINER_ENGINE=docker`). The stack is two
containers: `postgres:17-alpine` (Moodle 5.3 requires PostgreSQL 17) and
`moodlehq/moodle-php-apache:8.3` with the packaged Moodle release installed by CLI
on first start. From Git Bash on Windows, `export MSYS_NO_PATHCONV=1` first;
otherwise container paths such as `/var/www/html` are rewritten to Windows paths.

Moodle 5.0 moved questions into question bank modules (`mod_qbank`): a course
context can no longer hold question categories. The harness imports into the
course's default shared bank on 5.0+ and into the course context on 4.x.

```sh
scripts/moodle/moodle-rt.sh up 405        # default 502 = Moodle 5.2.x; 405 = 4.5.x, 503 = 5.3.x
scripts/moodle/moodle-rt.sh up 502        # stacks are per branch and can run side by side
QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py -v
scripts/moodle/moodle-rt.sh down          # remove all stacks (or: down 405)
```

Each test runs once per running stack (`qsafe-moodle-BRANCH-web`); with none running,
the tests fail rather than skip.

The test is skipped unless `QS_MOODLE_ROUNDTRIP` is set, so the regular
`uv run pytest` run stays container-free. The import/export inside the
container is driven by `scripts/moodle/roundtrip.php`, a CLI harness that
calls `qformat_xml` directly against a fresh course per run.
`scripts/moodle/format_text.php` renders texts with Moodle's `format_text()`, so a
test can check what the student's browser receives (used for markdown math).

When a new Moodle release is verified (or fails), add a row to the table above
with the test date.
