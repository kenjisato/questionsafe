# Roadmap

Development priorities, weighted toward validation and quality assurance,
new question types, and course operation. Written 2026-08-19 against commit `7b493ee`.

## A. Validation and quality assurance

Recommended first: everything else builds on trusting the XML we emit.

- Implement `questionsafe validate` (currently a `NotImplementedError` stub in `cli/project.py`).
  Two layers:
  1. Model validation: run `Question.validate()` across a file, directory, or project.
     This includes fixing a latent bug: `Reader.read(validate=...)` returns early for every
     type except cloze, so the flag is dead for 7 of 8 types (`importers/markdown.py`).
  2. XML well-formedness: parse the rendered output with lxml (declared as a dependency
     but currently unused).
- Moodle publishes no official XSD for the XML format, so schema validation cannot be the
  strategy. Instead, treat Moodle's importer as the oracle:
  - Compare our output against Moodle's own fixture XML
    (`public/question/format/xml/tests/fixtures/` in moodle/moodle; see `docs/references.md`).
  - Round-trip test on a real Moodle instance: import our XML, export it back, diff.
- Expand golden-file tests for the writer. Today the only golden file is
  `examples/markdown/cloze.xml`; add one per question type.

## B. New question types

The point of "Moodle-limited": support types R/exams does not.
Suggested order, easiest and most useful first:

1. `gapselect` (Select missing words) — `src/questionsafe/questions/gapselect.py` already
   exists as an empty placeholder; structurally close to multichoice with grouped options.
2. `matching` — pairs of subquestion/answer texts; widely used.
3. `ddwtos` (drag and drop into text) and `ddimageortext` — the drag-and-drop family shares
   much of gapselect's structure.
4. `ordering` — shipped as standard since Moodle 4.5.
5. The `calculated` family — see below.

For each type: model in `questions/`, `@ctx.register` handler in `writer/moodle/`,
`<type>.xml.j2` and `<type>.html.j2` templates, Reader support with front-matter schema,
authoring templates in `cli/templates/`, and a golden XML test.

On `calculated`: Moodle's wildcard/dataset machinery is complex and duplicates what
MetaChoice-style generation already does in Python. Generating static numerical variants
with a `QuestionGroup` under a subcategory plus a Moodle random question achieves the same
outcome with the existing design. Recommendation: extend the meta layer to numerical
questions (a `MetaNumerical` that samples parameters and computes answers) rather than
implementing the calculated XML. Revisit only if per-attempt server-side generation is required.

## C. Course operation and question bank management

- Grow the `course coverage` flow (CSV-based objectives in `analysis/coverage.py`) into a
  loop: report uncovered objectives, then scaffold question files for them via the existing
  `create` templates.
- Document a bank convention: category path structure, tag vocabulary, and idnumber scheme.
  `QuestionGroup.assign_idnumbers` and `Quiz.add_group` already implement the mechanics;
  what is missing is the documented convention and helpers to enforce it.
- Write a short guide on composing quizzes with Moodle-side random questions drawing from
  the subcategories `add_group` creates (see the Random question type entry in
  `docs/references.md`).

## D. Housekeeping (small, immediate)

- Delete the unreachable forwarder `src/questionsafe/cli.py`; the `cli/` package shadows it.
- Remove the duplicated `return self` in `MetaChoice.set_constraints`
  (`meta/metachoice.py:124`).
- Dependencies: `pydantic`, `textual`, `css-inline`, and `quarto` are declared but never
  imported; drop them or move them to the dev group (keep `lxml` if A adopts it).
  Conversely, `rich` and `PyYAML` are imported but only transitive; declare them explicitly.
- `docs/commandline.md` documents `init-course` and `coverage --course`, but the implemented
  commands are `course init` and `course coverage`; update the doc.
- `CHANGELOG.md` lacks the four MetaChoice commits of 2025-09-18 (`2d86e4b`..`7b493ee`).
- Decide the fate of the stray scratch file `unit/test.md` at the repository root.
- `docs/reference/` (committed) and `docs/api/` (gitignored quartodoc output) form two
  parallel reference trees; pick one as the source of truth.
