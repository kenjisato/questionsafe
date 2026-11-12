---
title: Command Line
---

The `questionsafe` command works on Markdown question files (see the
[Markdown Schema](markdown.qmd)). `questionsafe --help` and `questionsafe COMMAND --help`
list the options.

## A project

```bash
questionsafe init                  # scaffold the current directory
questionsafe create                # new question from a template (interactive)
questionsafe validate              # check every question under questions/
questionsafe render questions/q1.md --out q1.xml
```

### questionsafe init [DIR] [--force]

Scaffolds a project:

```
.
├── questions          # your Markdown questions
├── questionsafe.yml
└── templates          # copies of the question templates, *.md.j2
```

`--force` overwrites `questionsafe.yml` and the templates.

### questionsafe.yml

```yaml
project:
  questions: ./questions   # root for `create` and the default for `validate`
  templates: ./templates   # *.md.j2 templates for `create`
variables:
  ROOT: /path/to/shared    # $ROOT in include:, cloze file:, essay {path}
course:
  current: ECON101         # set by `questionsafe course checkout`
```

Without `project.templates`, the templates shipped with the package are used. Variables are
described in [Paths and variables](markdown.qmd#paths-and-variables).

## Questions

### questionsafe create [PATH] [--name NAME] [--type TYPE] [--force]

Writes a new question file from a template. Any of PATH, NAME, or TYPE that is omitted is
asked for interactively. A relative PATH resolves against `project.questions`.

```bash
questionsafe create questions/new.md --name "Sample/SC" --type singlechoice
```

TYPE is a template name: the file name of a `*.md.j2` template without the extension
(`numerical_unit.md.j2` is `--type numerical_unit`). Templates are Jinja2 and receive
`name` (the question name) and `VARS` (the `variables:` mapping).

### questionsafe validate [PATHS]... [--target MAJOR.MINOR]

Checks questions without importing them into Moodle: it reads each file, runs the model's
validation rules, renders Moodle XML, and checks that the XML is well-formed. PATHS are files
or directories (searched for `*.md`); the default is `project.questions`. With `--target`,
it also flags features that Moodle version does not understand (e.g., `idnumber` needs 3.6).
Exits non-zero if any file fails.

```bash
questionsafe validate questions/unit1/ --target 4.5
```

### questionsafe render FILE [--out PATH] [--templates-dir DIR]

Renders one Markdown question to a Moodle XML file you can import, or to stdout without
`--out`. `--templates-dir` overrides the XML templates (rarely needed).

## Courses

A course maps questions to learning objectives in CSV files, so you can see which objectives
your questions cover.

### questionsafe course init COURSE_ID [--title TITLE] [--dir DIR] [--force]

Creates `courses/COURSE_ID/` with three CSV files to edit:

```
# topics.csv
group,description
A,General
B,SNA

# objectives.csv
group,index,description
A,1,Can explain the purpose and targets of macroeconomics
B,1,Definition of GDP

# relationships.csv: question paths are relative to project.questions
group,index,question,difficulty
A,1,unit1/q1.md,1
```

### Other course commands

| Command | What it does |
|---|---|
| `questionsafe course checkout COURSE_ID` | Sets the current course in `questionsafe.yml` |
| `questionsafe course list` | Lists courses; marks the current one |
| `questionsafe course objectives [COURSE_ID]` | Lists the objectives |
| `questionsafe course questions [COURSE_ID]` | Lists question-to-objective links |
| `questionsafe course coverage [COURSE_ID]` | Reports coverage by group, uncovered objectives, and the questions covering each objective |

COURSE_ID defaults to the current course. `--dir` sets the base directory (default: the
current directory).

`build` and `preview` are reserved and not implemented.
