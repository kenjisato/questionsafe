# Changelog

## Unreleased

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
- Numerical precision policy updated:
  - Reader parses numeric answers via Decimal and quantizes to 1e-15 before converting to float.
  - NumericalAnswer equality now rounds value and tolerance to 15 decimal places (was 9).
  - Numerical CLOZE formatting uses 15 significant digits to avoid float tails.

### Removed
- Legacy MultiChoice sugar methods: correct(), wrong(), choices(), choice(), as_multiple(), numbering(), shuffle(). Examples and tests now use the new API.

### Tests
- Added tests/test_multichoice_set_choices.py to validate selective replacement behavior and uniform fraction distribution for set_choices_correct and set_choices_wrong.
- Added tests/test_markdown_reader_numerical.py to validate YAML "0.9" equals API 0.3+0.3+0.3 under the new precision policy.

### Docs
- README updated to document new MultiChoice and TrueFalse APIs and refined set_* semantics.
- Python API guide documents the Numerical precision and equality policy (Decimal→1e-15→float, equality at 15 dp).

