# Changelog

## Unreleased

### Added
- The Markdown reader reads numerical units (#16): `units:` as a list of
  `{name, multiplier}` and the options `unit_handling`, `unit_penalty`, `unit_penalty_of`,
  `unit_input`, `units_left`. Unknown keys are errors.
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

- `questionsafe validate [PATHS]... [--target MAJOR.MINOR]`: parses each Markdown
  question, runs model validation, renders it to Moodle XML and checks well-formedness
  (lxml), and optionally flags features the target Moodle version does not understand.
- Moodle version capability table (`writer/moodle/_versions.py`) with `parse_version`
  and `check_target`; the first version-gated entry is `idnumber` (Moodle 3.6+),
  verified against Moodle's `format.php` on stable branches.

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
- Unit multipliers in the docs, `examples/combined.py` and the `numerical_unit` templates
  ran the wrong way (km/h as 0.2777778 of m/s; kg as 1000 of g). A value in a unit is the
  base value times its multiplier: km/h is 3.6, kg is 0.001 (#16).
- `ShortAnswer.validate()` and `Numerical.validate()` require an answer worth 100%, as
  Moodle's edit forms do (#17); without one, no response could get full marks.
- Reader.read(validate=True) now actually validates every question type; previously all
  types except cloze returned before the validation step. Cloze-embedded fragment files
  are read with validate=False, since fragments need not be standalone-valid.
- Two documented shortanswer settings were not applied by the Markdown reader:
  `case_sensitive: true` had no effect (the reader called a method that does not exist and
  swallowed the error; it now sets `usecase`), and an `answers:` item without `fraction`
  got 0 instead of the documented 100 (the default of `ShortAnswer.add_answer`).
- `==` between choice questions (MultiChoice, SingleChoice, TrueFalse) ignores choice order
  (#15). The order-insensitive comparison in `Question.__eq__` never ran, because each
  `@dataclass` subclass generated its own field-by-field `__eq__`; it is removed. Other
  question types compare answers in order (Moodle grades shortanswer and numerical by the
  first matching answer).
- The Markdown reader ignored the documented full-form keys `answernumbering`,
  `shuffleanswers` and `single`, and swallowed errors in `choice_layout:` (#11). They are
  now read; giving a key and its `choice_layout:` counterpart is an error, and so is an
  unknown `choice_layout:` key.
- `MultiChoice` with `set_single_choice()` accepts partial credit as Moodle does (#13):
  one answer at 100% is required and the sum of positive fractions is no longer checked
  (e.g. 100/50/0 used to fail with "Sum of positive fractions must be 100").
  `SingleChoice` still allows exactly one positive answer.
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
- Numerical unit options follow Moodle's edit form (#16): `UnitSpec` has `handling`
  (`none`/`optional`/`graded`), `penalty` (any value 0-1), `penalty_of`
  (`response`/`question`), `input` (`text`/`radio`/`select`) and `left`, replacing the
  Moodle codes `showunits`, `unitgradingtype`, `unitpenalty`, `unitsleft`. The old
  `showunits` was documented as "1 = required/graded", but with graded units Moodle reads
  1 as "choose the unit with radio buttons", so units were shown as radio buttons by
  default, and a drop-down could not be chosen. Defaults are now Moodle's: optional,
  penalty 0.1 of the response grade, text input. `validate()` requires a unit when units
  are used and the first unit's multiplier to be 1, as the edit form does.
- Choice numbering defaults to `abc`, Moodle's default (#11); it was `none`. Questions
  that never set it now show a./b./c. in Moodle. Set `numbering: none` (or
  `set_numbering("none")`) to keep the old look.
- `labels` is renamed `numbering` (#11): the `MultiChoice.numbering` attribute,
  `set_numbering()`, `set_choice_layout(numbering=...)` and `choice_layout: {numbering: ...}`.
- Numerical Markdown schema: the numeric value key in full-form `answers` items is
  `answer` (matching the documented schema, authoring templates, and
  `Numerical.add_answer`); the reader previously required an undocumented `value` key,
  which silently produced questions with no answers.
- The numerical shorthand `answer:` accepts only a scalar; the undocumented mapping form
  (`answer: {value, tolerance, feedback}`) now raises ValueError. Use full-form `answers`
  for tolerance/feedback.
- Numerical precision policy updated:
  - Reader parses numeric answers via Decimal and quantizes to 1e-15 before converting to float.
  - NumericalAnswer equality now rounds value and tolerance to 15 decimal places (was 9).
  - Numerical CLOZE formatting uses 15 significant digits to avoid float tails.
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

### Deprecated
- `labels` (#11): `MultiChoice.labels`, `set_labels()` and `set_choice_layout(labels=...)`
  still work and emit a `DeprecationWarning`; `choice_layout: {labels: ...}` in Markdown
  emits a `FutureWarning`, which is shown by default. They will be removed in a later release.
- `showunits`, `unitgradingtype`, `unitpenalty`, `unitsleft` keywords of `add_units()`,
  `set_units()` and `set_unit_options()` (#16) still work, mean what they did, and emit a
  `DeprecationWarning`.

### Removed
- `Unit.fraction` (#16): Moodle's `<unit>` has no fraction, and the importer ignored it.
- `randomize_branch` on `MetaChoice.generate_*` and `constrained_subsets`; the
  usage-balanced search replaces it. `randomize_order` now only breaks ties.
- Legacy MultiChoice sugar methods: correct(), wrong(), choices(), choice(), as_multiple(), numbering(), shuffle(). Examples and tests now use the new API.

### Tests
- Added tests/test_multichoice_set_choices.py to validate selective replacement behavior and uniform fraction distribution for set_choices_correct and set_choices_wrong.
- Added tests/test_markdown_reader_numerical.py to validate YAML "0.9" equals API 0.3+0.3+0.3 under the new precision policy.

### Docs
- README updated to document new MultiChoice and TrueFalse APIs and refined set_* semantics.
- Python API guide documents the Numerical precision and equality policy (Decimal→1e-15→float, equality at 15 dp).
- Docs restructured (#14): `markdown.qmd` is the single Markdown schema reference (type aliases,
  `include:`, path variables, shorthands, cloze); `python.qmd` covers only the Python API
  (absorbing `usage.qmd`); `commandline.md` matches the actual CLI and is in the sidebar; new
  Quickstart and index; the site's changelog includes this file instead of a diverging copy;
  README regenerated.
