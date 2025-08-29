## General Rules

* Codebase optimization is prioritized over backward compatibility.
* Never introduce code just for backward compat. Simply delete old code and rewrite tests and docs.

## Rules for Python Project

* Run all Python scripts and third-party programs through uv runner.
  * `uv run pytest` not `pytest` 
  * `uv run path/to/script.py` not `python path/to/script.py`
  * `uv run ruff check`
  * `uv run quarto render` , etc.
  

## Naming convention

* For user-facing objects, consider giving IDE-friendly names with 
  common prefix.

In this project,

* Methods prefixed with `set_` update an attribute.
* Medthos prefixed with `add_` append one item to a list-type attribute.


## Documentation

- Main documentation in `doc` directory. Render with `quarto` and `quartodoc`
- README.md is generated with `quarto render README.qmd`. Do not edit README.md manually. 


## API Design Philosophy

- Favor clarity and consistency over backward compatibility.
  - Remove redundant/legacy APIs quickly and update tests/docs (e.g., Cloze.encode removed; use instance .cloze()).
- Provide two tiers of APIs:
  - "Safe" (aka "colorful") methods that are validation-proof and guard against non-typical usage.
  - Low-level setters/adders for advanced scenarios; these may require manual validation awareness.


## Safe API Contract

- Safe methods are tagged with a decorator and marked in docstrings.
  - Decorator: base._safe.safe_api
  - Docstrings are prefixed with [SAFE] for IDE visibility.
  - Introspection helper: questionsafe.base.list_safe_apis (also re-exported at top-level).
- Principle: After any chain of safe calls, validate() should pass without further changes.

Current safe methods
- MultiChoice
  - set_choices_correct
  - set_choices_wrong (fraction must be in allowed set)
  - add_choice_correct (recalculates uniform distribution; snaps to allowed fractions)
  - add_choice_wrong (guards fraction to allowed set)
- SingleChoice
  - set_choice_correct (overwrites to exactly one correct=100; removes conflicting wrong duplicate)
  - add_choice_correct (guarded: raises if a correct already exists)
- TrueFalse
  - set_correct_if_true
  - set_correct_if_false
  - Note: set_choice_correct/set_choice_wrong are not safe because they accept arbitrary text; they delegate to SingleChoice semantics but are not parameterless.


## Validation Rules (selected)

- MultiChoice
  - Positive fractions must sum to 100.
  - Fractions must come from Moodle's allowed set (including negatives).
  - add_choice_correct behavior under safe contract:
    - First correct -> 100.
    - If existing corrects are uniform and sum to 100, recompute uniform = 100/(n+1) and snap to allowed.
    - If cannot snap (e.g., 100/11), or not uniform/sum!=100 -> raise; suggest set_answers.
- SingleChoice
  - Exactly one correct with fraction=100; no other positive fractions.
- TrueFalse
  - Exactly two answers with texts 'true' and 'false' (case-insensitive).


## Answer API Consistency

- ShortAnswer.add_answer default fraction = 100.0.
- Numerical.add_answer signature uses parameter name answer and accepts NumericalAnswer | float | int (NumericalAnswerLike).


## CLOZE Embedding

- Prefer calling .cloze() on question instances (SingleChoice, MultiChoice, ShortAnswer, Numerical).
- Orientation parameter typed as Optional[Literal["v","h"]] and mapped in per-type docstrings.
- Precheck validates weights and content; numerical answers are excluded from "non-empty text" checks.


## Utilities

- base._constraints.uniform_fraction(n): returns 100.0/n (n>0).
- base._constraints.snap_allowed_positive(value, tol=1e-4): snap to canonical allowed positive fraction or return None.


## Tooling Convenience

- list_safe_apis is available via:
  - from questionsafe.base import list_safe_apis
  - from questionsafe import list_safe_apis
