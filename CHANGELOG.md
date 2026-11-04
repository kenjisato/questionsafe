# Changelog

## Unreleased

### Added
- Local images in question text and choices (#3): `![alt](path)` and `<img src="path">`
  are embedded as Moodle files named by content hash; in choices the alt text becomes
  `Choice image` and the title is dropped. The Markdown reader resolves relative paths
  against the question file. Raster images only (SVG is an error). With shuffle on,
  multichoice answers are written in an order fixed by a hash of their text, so the
  answer ids that Moodle shows in image URLs do not reveal the authoring order. Verified
  on Moodle 4.5 and 5.2 (import, export, and the attempt display).
- Choices in the Markdown body: singlechoice / multichoice / truefalse files can list
  choices as a checkbox list under a reserved heading `## /choices` (any level)
  instead of front matter `choices:` (#5). Headings starting with `/` are reserved;
  an unknown name is an error, and `{.noqs}` keeps such a heading as question text.
- Named scoring rules for wrong choices, after R/exams' `exams_eval`:
  `MultiChoice.set_scoring(rule)` (also `SingleChoice`) sets every wrong choice to
  `false2` (-1/max(n_wrong, 2)), `false`, `true`, `all`, or `none`, snapped to a
  Moodle fraction. `Cloze.set_scoring(rule)` applies the rule to embedded choice gaps.
- Markdown authoring format for MetaChoice (`type: metachoice`): pool, stems, and
  constraints in front matter; correctness and per-stem exclusions in a body
  ```csv matrix (`x` = correct, empty = eligible, `-` = never sampled).
  Read with the new `Reader.read_metachoice()`; all key references are resolved
  at read time with the offending key named. `Reader.question_type()` returns the
  resolved front-matter type without building a question.
- `MetaChoice.validate()`: template-level checks (key resolution, constraint
  bounds, exclusion feasibility) without generating. `questionsafe validate`
  now validates `type: metachoice` files at the template level.
- First-class per-stem exclusions: `Stem.set_choices_excluded()` and
  `MetaChoice.add_stem(exclude=...)` via the reserved `__excluded__` group.
- `MetaChoice(name=..., source=...)`: variants are named `{name}/{stem key}`
  when `name` is set, and `source` propagates to `QuestionGroup.source`.
- Example: `examples/markdown/metachoice.md` + `examples/metachoice_md.py`
  (three stems sharing one pool, exclusions that matter, scoped constraints).
- Round-trip test against a real Moodle in a Podman container
  (`tests/test_moodle_roundtrip.py`, opt-in via `QS_MOODLE_ROUNDTRIP=1`;
  stack managed by `scripts/moodle/moodle-rt.sh`, import/export driven by
  `scripts/moodle/roundtrip.php` through Moodle's own `qformat_xml`).
  Verified versions are recorded in `docs/moodle-compat.md` (4.5 LTS: OK,
  2026-08-29, including the snapped 33.33333 fractions).
  Stacks are per Moodle branch (`moodle-rt.sh up 405`, `up 502`) and can run side
  by side; each round-trip test runs once per running stack.

### Changed (MetaChoice / MultiChoice fractions)
- `Stem.text` widened to `Text | str`; `add_stem` no longer flattens a `Text`
  stem to plain text, so `format: markdown` survives to the generated question.
- `add_stem` rejects duplicate stem keys.
- Uniform correct fractions now snap to Moodle-supported values in both
  `MultiChoice.set_choices_correct` and MetaChoice generation (e.g. three
  corrects get 33.33333 each, not 100/3); unsnappable splits raise `ValueError`.
  `MultiChoice.validate()` allows the resulting rounding headroom in the
  positive-fraction sum (1e-3 instead of 1e-6).

### Fixed
- Choices and feedback were written as `format="html"` whatever the author wrote, so
  Markdown in them was shown literally (#8). The Markdown reader now gives every plain-string
  text (choices, answer and combined feedback, hints, essay grader info, MetaChoice choices
  and stems) the file's format (`format` / `questiontext_format`, default `markdown`), and
  the multichoice writer emits each choice's own format. `SingleChoice.set_choice_correct` /
  `add_choice_correct` and the `MultiChoice` choice setters accept `Text` to set it from
  Python. Math in markdown choices is escaped as in #7. Questions read from Markdown files
  now compare equal to Python-built ones only when the choices are given as
  `Text(..., format="markdown")`. A singlechoice checkbox list without exactly one correct
  choice now fails at read time, as the `correct`/`wrong` mapping already did.
  Grader info `{text, format}` in a Markdown file, which raised `TypeError`, now works.
- Essay response template: `{text, format}` (in Markdown files and from Python) reached the
  student as the mapping's repr, and a markdown template had its math escaped as in #7, which
  the student saw, since Moodle pre-fills the answer box with the template unformatted. Both
  are now written as given.
- TeX in `format: markdown` texts reached the student broken: Moodle's Markdown
  converter dropped the backslash of `\(` / `\[` and read `*` / `_` inside math as
  emphasis (#7). The Moodle writer now backslash-escapes Markdown specials inside
  math spans in markdown texts (question text, feedback, hints, essay grader info,
  cloze stem outside the gaps); the format stays `markdown`.
  `Cloze.compile_text(text=None)` takes the template to fill. Verified on Moodle
  4.5 and 5.2 with `format_text()` (`scripts/moodle/format_text.php`).
- `MetaChoice.generate_singlechoice` / `generate_multichoice` with a `limit` smaller
  than the number of feasible subsets returned variants that shared their early
  picks, often all with the same correct choice (#4). Each variant is now the first
  feasible, not yet generated subset when choices are ranked by how often they
  have appeared so far, so variants cycle through the correct choices and the
  distractors. Output for a given `seed` differs from earlier versions.
- Cloze questions dropped their general feedback from the Moodle XML.
- `SingleChoice.cloze()` dropped negative fractions, so a wrong choice in an
  MC/MCV/MCH gap could not deduct points. They are now kept, as in `MultiChoice.cloze()`.
- Duplicated `return self` in `MetaChoice.set_constraints`.
- `MultiChoice.set_choices_correct` with three or more corrects produced
  fractions rejected by `validate()`, violating the safe-API contract.

### Changed
- MultiChoice API overhauled for clarity and EAFP-friendly usage:
  - Added verbose methods:
    - add_choice_correct(text, feedback=None) — appends a 100% correct choice
    - add_choice_wrong(text, fraction=0.0, feedback=None) — appends a wrong/partial choice
    - set_choices_correct(*texts, feedback=None) — replaces only positive-fraction answers and distributes 100% uniformly across provided texts (100/N)
    - set_choices_wrong(*texts, fraction=0.0, feedback=None) — replaces only zero/negative-fraction answers with provided texts and fraction
  - set_single() and set_multiple() now take no arguments.
  - set_shuffle(on=True) replaces the old shuffle(on) method (removed).
  - Low-level add_answer()/set_answers() remain as primitives.
- TrueFalse implementation updated:
  - Provides set_correct("true"|"false", feedback=None) and set_wrong("true"|"false", feedback=None).
  - Internally uses MultiChoice add_choice_*.
  - Current semantics: subsequent calls overwrite (do not preserve previous feedback unless explicitly provided).

### Removed
- `randomize_branch` on `MetaChoice.generate_*` and `constrained_subsets`; the
  usage-balanced search replaces it. `randomize_order` now only breaks ties.
- Legacy MultiChoice sugar methods: correct(), wrong(), choices(), choice(), as_multiple(), numbering(), shuffle(). Examples and tests now use the new API.

### Tests
- Added tests/test_multichoice_set_choices.py to validate selective replacement behavior and uniform fraction distribution for set_choices_correct and set_choices_wrong.

### Docs
- README updated to document new MultiChoice and TrueFalse APIs and refined set_* semantics.
