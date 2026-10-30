# API Overview

A one-file map of the questionsafe package for developers and coding agents.
For rendered per-object reference pages, see the API Reference section of the docs site.

## Package map

| Package | Contents |
|---|---|
| `questionsafe.base` | `Question` base class, `Text`/`Hint`/`Feedback`/`GraderInfo`, `Answer` facade, `Choice`, constraint sampling, `QuestionGroup`, Moodle fraction/penalty constants, `safe_api` tooling |
| `questionsafe.questions` | The nine question models (see below); exposed as the `Q` facade |
| `questionsafe.quiz` | `Quiz` container with category/group handling and `to_xml`/`to_html` |
| `questionsafe.writer.moodle` | Moodle XML/HTML rendering: singledispatch context builders + Jinja2 templates |
| `questionsafe.importers` | `Reader`: Markdown/front-matter files to question objects |
| `questionsafe.meta` | `MetaChoice`: variant generation from a choice pool with constraints |
| `questionsafe.analysis` | CSV-driven learning-objective coverage (`analyze_csv_course`) |
| `questionsafe.cli` | Typer app: `init`, `create`, `render`, `course *` |

## Top-level exports

```python
from questionsafe import (
    Q,            # questions facade: Q.MultiChoice, Q.Numerical, ...
    Quiz,
    Text, Hint, Feedback, Unit, Answer,
    render_xml, render_html, write_xml, write_html,
    list_safe_apis,
    Reader,
)
from questionsafe.meta import MetaChoice, Stem, Constraint  # not re-exported at top level
```

## Question types

All types subclass `Question` (`base/_question.py`) and share:
`set_name`, `set_questiontext` (aliases `set_question`, `ask`), `set_feedback_general`,
`set_defaultgrade`, `set_tags`/`add_tag`, `set_idnumber`, `add_answer`/`set_answers`, `validate()`.
Types with hints mix in `MultiTryMixin` (`add_hint`, `set_hints(..., penalty="auto")`, `set_penalty`);
choice types mix in `CombinedFeedbackMixin` (`set_feedback_correct/partiallycorrect/incorrect/combined`).

| Class | Moodle XML type | Notable methods |
|---|---|---|
| `Q.MultiChoice` | `multichoice` | `set_choices_correct/wrong`, `add_choice_correct/wrong`, `set_scoring` (safe), `set_single_choice`, `set_labels`, `set_choice_layout`, `set_shuffle`, `.cloze()` |
| `Q.SingleChoice` | `multichoice` with `<single>true</single>` | `set_choice_correct` (safe), guarded `add_choice_correct`, `.cloze()` |
| `Q.TrueFalse` | `truefalse` | `set_correct_if_true/false` (safe) |
| `Q.Numerical` | `numerical` | `add_answer(answer, tolerance, ...)`, `add_units`/`set_units`, `set_unit_options`, `.cloze()` |
| `Q.ShortAnswer` | `shortanswer` | `add_answer` (fraction defaults to 100), `set_usecase`, `.cloze()` |
| `Q.Essay` | `essay` | ~14 setters over `EssayTextArea`/`EssayAttachments`/`EssayResponse` options |
| `Q.Description` | `description` | display-only text |
| `Q.Cloze` | `cloze` | `embed_question(q, orientation, weight)`, `set_scoring(rule)`, `compile_text()` |
| `Q.Category` | `category` pseudo-question | `Category(path)`; path is normalized with `$course$/` |

Safe methods and validation rules are specified in `AGENTS.md` (Safe API contract);
enumerate them at runtime with `list_safe_apis(obj)`.

## Building blocks

- `Text(text, format="html", options={})` — rich text value; `format` may be `html`,
  `markdown`, `plain_text`, passed through to Moodle as-is. `Hint`, `Feedback`,
  `GraderInfo` subclass it and offer `.from_text()`.
- `Answer.from_text(text, fraction=...)` / `Answer.from_num(value, tolerance=..., fraction=...)` —
  user-facing constructors for `TextAnswer` / `NumericalAnswer`.
- `Choice(key, text)` — frozen key/text pair shared by MetaChoice and choice sampling.
- `base._constraints` — Moodle's allowed fraction/penalty sets and snapping helpers.
- `QuestionGroup(variants=[...])` — a bundle of variants; `assign_idnumbers(prefix, offset)`.

## Quiz

```python
quiz = Quiz(title=..., category="Parent", subcategory_id="123")  # or "name"
quiz.add(q1, q2, ...)                     # questions and Category nodes
quiz.add_category("Sub", inherit=True)    # appends Category("Parent/Sub")
quiz.add_group(group, idnumber_prefix="v")  # inserts a subcategory + idnumbers
quiz.validate()
xml_bytes = quiz.to_xml()                 # or quiz.to_xml("out.xml") -> Path
html_str = quiz.to_html(title=...)        # HTML preview
```

`len(quiz)` counts non-category questions. `lms` is `"moodle"` only; other values raise
`NotImplementedError` (extension point).

## MetaChoice (variant generation)

Runnable examples: `sandbox/metachoice_example.py` (Python API) and
`examples/metachoice_md.py` (Markdown authoring).

```python
from questionsafe.meta import MetaChoice, Constraint

mc = MetaChoice(name="Bank/Q1")  # optional; variants are named "{name}/{stem key}"
mc.set_choices({"A": "text a", "B": "text b", "C": "text c", "D": "text d"})  # Mapping only
mc.add_constraint("A", "B", min=0, max=1, id="pair")     # global constraint
mc.add_stem(
    "q1", "Which of the following ...?",
    correct=["A"],                                        # reserved "__correct__" group
    exclude=["D"],                                        # reserved "__excluded__" group (min=0, max=0)
    constraints={"local": Constraint("C", "D", min=1)},   # per-stem constraints
)
mc.validate()  # template-level checks (keys, bounds, exclusion feasibility)
group = mc.generate_multichoice(n=4, limit=3, seed=42, nc=1, prototype=None)
group2 = mc.generate_singlechoice(n=4, limit=3, seed=42)  # forces exactly one correct
```

- `generate_*` returns a `QuestionGroup` (with `source` set from `MetaChoice.source`);
  feed it to `Quiz.add_group`.
- With k correct choices in a subset, fractions snap to the Moodle value closest to
  100/k; unsnappable splits (e.g., k=11) raise `ValueError`.
- `nc` fixes the number of correct choices per subset (int or `(min, max)`).
- Variants spread over the pool: each is the first feasible, not yet generated subset
  with the least-used choices ranked first (`seed` breaks ties).
- `prototype` is a question deep-copied per variant to carry defaults
  (shuffle, labels, combined feedback); its answers are replaced.
- Sampling is a DFS over subsets (`base._choice_sampling.constrained_subsets`) with
  per-stem seeds derived from `seed`.
- `Stem.set_choices_excluded(keys)` mirrors `set_choices_correct`; `add_stem(exclude=...)`
  is the usual entry point. Correct and excluded sets must not overlap.

## Reader (Markdown import)

```python
q = Reader("question.md").read(validate=True)
mc = Reader("template.md").read_metachoice(validate=True)  # type: metachoice files
Reader("question.md").question_type()                      # resolved type, no build
```

Front-matter `type:` accepts aliases: `singlechoice|single|sc`, `truefalse|tf`,
`multichoice|multiple|multi|mc`, `numerical|num`, `shortanswer|short|sa`, `essay`,
`description|desc`, `cloze`. `type: metachoice` is a template, not a question:
`read()` rejects it and `read_metachoice()` returns a `MetaChoice` (schema in
`markdown.qmd`, worked example in `examples/markdown/metachoice.md`). The per-type
schema is documented in `markdown.qmd`; authoring templates live in
`src/questionsafe/cli/templates/*.md.j2`.

## XML generation pipeline

1. `writer/moodle/_build.py` defines a singledispatch `ctx`; each `writer/moodle/<type>.py`
   registers a handler that turns a question into a plain dict
   (`utils.base_question(q)` supplies the shared fields).
2. `_common.to_context` normalizes a `Quiz`, iterable, or single question into a context list.
3. `_templating.make_env(user_dir, kind)` builds a Jinja2 environment
   (user templates override packaged ones; filters: `cdata`, `xmlbool`, `numscheme`, `slug`).
4. `_quiz.xml.j2` includes `<type>.xml.j2` per question; a parallel `*.html.j2` set renders previews.
5. `render_xml(obj, *, templates_dir=None) -> bytes`; `write_xml(obj, file, ...) -> Path`;
   `render_html/write_html` likewise.

There is no schema validation of the output; correctness relies on templates plus
`Question.validate()`. See `docs/roadmap.md`.

## CLI

- `questionsafe init [DIR]` — scaffold `questions/`, `templates/`, `questionsafe.yml`
- `questionsafe create [PATH] --type ...` — new question file from a template (interactive fallback)
- `questionsafe render FILE [--out] [--templates-dir]` — Markdown to XML
- `questionsafe validate [PATHS]... [--target MAJOR.MINOR]` — model rules + XML
  well-formedness + version-gated feature check (see `writer/moodle/_versions.py`)
- `questionsafe course init|coverage|checkout|list|objectives|questions` — CSV-based course tools
- `build`, `preview` — reserved stubs (`NotImplementedError`)

## Known gaps

- `questions/gapselect.py` is an empty placeholder.
- CLI `build`/`preview` are unimplemented.
- Only golden-file test for writer output is `examples/markdown/cloze.xml`.
- `Quiz.lms` supports `"moodle"` only.
