---
title: Command Line Interface
---

# Command Line Interface

## Installation

- Installed with the package and exposed as the `questionsafe` command.
- Run all commands via uv in this project: `uv run questionsafe ...`

## Commands

### questionsafe render FILE [--out PATH] [--templates-dir DIR]

Render a single Markdown question file (with YAML front matter) into a single-question Moodle XML `<quiz>`.

- FILE: path to a Markdown file.
- --out: output XML path; if omitted, XML is written to stdout.
- --templates-dir: override built-in XML templates (rarely needed).

### questionsafe create [PATH] [--name NAME] [--type TYPE] [--force]

Create a new Markdown question file from a template.

- The template set is discovered dynamically from `questionsafe.yml` (see below). If absent, package-shipped templates are used.
- If any of PATH/NAME/TYPE is omitted, an interactive prompt (InquirerPy) is used.
- If `project.questions` is set in `questionsafe.yml`, relative PATH is resolved against that root.

Examples:
- `uv run questionsafe create` (interactive)
- `uv run questionsafe create questions/new.md --name "Sample/SC" --type singlechoice`
- `uv run questionsafe create tf.md --name Logic/DM --type truefalse --force`

### questionsafe init [DIR] [--force]

Scaffold a project directory with config and templates.

- DIR: target directory (defaults to current directory).
- Creates:
  - `questions/` (root for authored Markdown questions)
  - `templates/` (copy of default templates)
  - `questionsafe.yml` with defaults
- `--force` overwrites `questionsafe.yml` and replaces existing templates.

Resulting layout:

```
.
├── questions
├── questionsafe.yml
└── templates
    ├── essay.md.j2
    ├── multichoice.md.j2
    ├── singlechoice.md.j2
    └── ...
```

### questionsafe init-course COURSE_ID [--title TITLE] [--dir DIR] [--force]

Scaffold a course directory with CSVs describing topics, objectives, and relationships.

Creates:
- courses/COURSE_ID/topics.csv         (group, description)
- courses/COURSE_ID/objectives.csv     (group, index, description)
- courses/COURSE_ID/relationships.csv  (group, index, question, difficulty)

### questionsafe coverage --course COURSEDIR

Analyze how broadly your questions cover course objectives, per course.

- Reads CSV files from the course directory:
  - topics.csv: group,description
  - objectives.csv: group,index,description
  - relationships.csv: group,index,question,difficulty
- Scans questions under `project.questions` (from questionsafe.yml) to display friendly names where available.

Example CSVs:

```
# topics.csv
group,description
A,General
B,SNA

# objectives.csv
group,index,description
A,1,Can explain the purpose and targets of macroeconomics
A,2,Can choose macroeconomic variables
B,1,definition of GDP
B,2,definition of implicit deflator

# relationships.csv
group,index,question,difficulty
A,1,unit1/q1.md,1
B,1,unit2/q3.md,2
```

Output is a textual report including coverage by group, uncovered objectives, and a per-objective list of covering questions.

### questionsafe build, validate, preview

Reserved for future features.

## Project configuration (questionsafe.yml)

Place `questionsafe.yml` in your project root to control authoring roots and template discovery.

```yaml
project:
  questions: ./questions   # default root used by `questionsafe create`
  templates: ./templates   # directory containing *.md.j2 templates
```

- `project.questions`: The root directory for authoring; `questionsafe create` resolves relative paths against this root and uses it for the default output path in interactive mode.
- `project.templates`: If present, templates are loaded from here; otherwise, package defaults are used.

## Template discovery and authoring

- Files named `*.md.j2` in the template directory are available as template names using their filename stem.
  - Example: `numerical_unit.md.j2` -> `--type numerical_unit`
- Rendering is with Jinja2; the following variables are available in the context:
  - `name`: The question name to place in front matter
- Example built-in templates:
  - `singlechoice.md.j2`, `multichoice.md.j2`, `truefalse.md.j2`, `shortanswer.md.j2`, `numerical.md.j2`, `numerical_unit.md.j2`, `cloze.md.j2`, `essay.md.j2`
- Cloze template uses Jinja2 raw blocks to show literal `{{gap}}` placeholders without being interpreted by Jinja.
