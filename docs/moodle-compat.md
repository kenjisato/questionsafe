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
| 4.5.13+ (Build: 20260818) | OK | 2026-08-29 | multichoice (incl. 33.33333 fractions), singlechoice, truefalse, shortanswer, numerical (tolerance + unit), essay, description, cloze, MetaChoice-generated variants (14 questions) |

"OK" means: import with `matchgrades=error` and `stoponerror=1` succeeded, and
for the answer-bearing types the re-exported questions carried the same
question texts, answer texts, fractions, tolerances, and units. Essay,
description, and cloze are checked for identity (name + type) since Moodle
reconstructs their bodies from parsed parts.

## Running the round-trip test

Requires Podman (or Docker via `QS_CONTAINER_ENGINE=docker`). The stack is two
containers: `postgres:16-alpine` and `moodlehq/moodle-php-apache:8.3` with the
packaged Moodle release installed by CLI on first start.

```sh
scripts/moodle/moodle-rt.sh up 405        # 405 = Moodle 4.5.x; 500 = 5.0.x, etc.
QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py -v
scripts/moodle/moodle-rt.sh down          # remove containers when done
```

The test is skipped unless `QS_MOODLE_ROUNDTRIP` is set, so the regular
`uv run pytest` run stays container-free. The import/export inside the
container is driven by `scripts/moodle/roundtrip.php`, a CLI harness that
calls `qformat_xml` directly against a fresh course per run.

When a new Moodle release is verified (or fails), add a row to the table above
with the test date.
