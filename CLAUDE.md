@AGENTS.md

# Claude guardrails

- Run everything through `uv run` (`uv run pytest`, `uv run ruff check`, `uv run script.py`).
- New features start with a failing test. Before claiming any work complete, run `uv run pytest`
  and confirm it passes.
- Never hand-edit generated files: `README.md` (edit `README.qmd` instead) and `docs/reference/`.
- For Moodle XML elements, attributes, or cloze syntax, consult `docs/references.md` and the sources
  it lists. Do not invent XML structure from memory; when in doubt, check Moodle's own
  `format.php` and its fixture XML files.
- A breaking API change updates tests, docs, examples, and `CHANGELOG.md` in the same commit.
