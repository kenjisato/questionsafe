# Changelog

## Unreleased

### Added
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
- Legacy MultiChoice sugar methods: correct(), wrong(), choices(), choice(), as_multiple(), numbering(), shuffle(). Examples and tests now use the new API.

### Tests
- Added tests/test_multichoice_set_choices.py to validate selective replacement behavior and uniform fraction distribution for set_choices_correct and set_choices_wrong.

### Docs
- README updated to document new MultiChoice and TrueFalse APIs and refined set_* semantics.
