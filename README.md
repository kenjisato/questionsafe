# SingleChoice


# questionsafe

Build Moodle quizzes (XML) from Python.

## Highlights

- Python API for composing questions: `MultiChoice`, `TrueFalse`,
  `ShortAnswer`, `Numerical`, `Essay`, `Description`
- Render to Moodle XML and HTML preview using
  [Jinja2](https://jinja.palletsprojects.com/en/stable/)
- CLI and examples for quick usage \[TODO\]

## Install

``` bash
pip install questionsafe
```

## TrueFalse

``` python
from questionsafe import Q, render_xml

tf = (
    Q.TrueFalse("Logic/DeMorgan")
    .ask("Not(A and B) == (Not A) or (Not B)")
    .set_correct_if_true()
)

print(render_xml(tf).decode("utf-8"))

# <?xml version="1.0" encoding="UTF-8"?>
# <quiz>
# 
# <question type="truefalse"><name><text>Logic/DeMorgan</text></name>
#   <questiontext format="html">
#     <text><![CDATA[Not(A and B) == (Not A) or (Not B)]]></text>
#   </questiontext><defaultgrade>1.0</defaultgrade>
#   <answer fraction="100.0" format="html">
#     <text>true</text>
#   </answer>
#   <answer fraction="0.0" format="html">
#     <text>false</text>
#   </answer>
#   <idnumber></idnumber>
# </question>
# </quiz>
```

``` python
from questionsafe import Q, Text

sc = (
    Q.SingleChoice("Capital/Thailand (single)")
    .ask("What is the capital of Thailand?")
    .set_choice_correct("Bangkok")
    .set_choices_wrong("Chiang Mai", "Phuket", "Pattaya")
)
print(sc)

# SingleChoice('Capital/Thailand (single)', 'What is the capital of Thailand?...', ...)
```

## MultiChoice

``` python
from questionsafe import Q

mcq = (
    Q.MultiChoice(
        name="Capital/Thailand",
        questiontext=Text("What is the capital of **Thailand**?", format="markdown")
    )
    .add_choice_correct("Bangkok", feedback="Right!")
    .set_choices_wrong("Chiang Mai", "Phuket", "Pattaya")
    .set_numbering("abc")
    .set_shuffle(True)
)
```

API summary for `MultiChoice`

- `add_choice_correct(text, feedback=None)`
- `add_choice_wrong(text, fraction=0, feedback=None)`
- `set_choices_correct(*texts, feedback=None)` (uniform 100/N)
- `set_choices_wrong(*texts, fraction=0, feedback=None)`
- Low-level: `add_answer(answer)`, `set_answers(*answers)`
- Other: `set_single()`, `set_numbering(scheme)`, `set_shuffle(on=True)`

## ShortAnswer

``` python
from questionsafe import Q

sa = (
    Q.ShortAnswer("SA")
    .ask("Spell 'colour'")
    .add_answer("colour")
)
```

## Numerical (without unit)

``` python
from questionsafe import Q

nu = (
    Q.Numerical("NU")
    .ask("2 + 2?")
    .add_answer(4)
)
```

## Bundling with Quiz

``` python
from questionsafe import Q, Quiz, Text

quiz = Quiz(category="Sample/Week1")
quiz.add(
    Q.TrueFalse(
        name="Logic/DeMorgan",
        questiontext=Text("<p>Not(A and B) == (Not A) or (Not B)</p>")
    ).set_correct_if_true()
)
quiz.add(
    Q.SingleChoice(
        name="Capital/Thailand (single)",
        questiontext=Text("<p>What is the capital of Thailand?</p>")
    ).set_choice_correct("Bangkok").set_choices_wrong("Chiang Mai", "Phuket")
)
quiz.to_xml("build/week1.xml")
quiz.to_html("build/week1.html")
```

> Other question types and advanced usages (e.g., units for Numerical)
> are covered in the documentation.

## Categories

``` python
from questionsafe.quiz import Quiz

# Inherit the parent category when adding a subcategory
quiz = Quiz(category="Course/Week1").add_category("Intro")
xml_bytes = quiz.to_xml()
```

- `add_group()` will also insert Category nodes for you when grouping
  variants.

### Note: `len(quiz)` counts only non-category questions; category nodes are ignored.

Hints and penalty (auto behavior)

For question types supporting multiple tries (MultiTryMixin),
set_hints(…) can also set the per-try penalty. By default
penalty=“auto”, which computes 1/(1 + number_of_hints), then snaps to
the nearest Moodle-supported penalty value. This matches the intuition
that a student reaches 0 points by the last attempt.

Examples - 0 hints -\> 1.0 - 1 hint -\> 0.5 - 2 hints -\> ~0.3333333 - 3
hints -\> 0.25 - 4 hints -\> 0.2

You can override this via penalty=<float>, or pass penalty=None to leave
the current penalty unchanged when replacing hints.

## Ergonomics: setting the question text

You can pass questiontext in the constructor or set it fluently later.
The following are equivalent:

``` python
from questionsafe import Q

Q.MultiChoice(name="MC2", questiontext="<p>Pick all that apply</p>")
Q.MultiChoice("MC2").set_question("<p>Pick all that apply</p>")
Q.MultiChoice("MC2").ask("<p>Pick all that apply</p>")
```

Note - Validation enforces that questiontext is non-empty. If you
construct without a questiontext, make sure to set it via
.set_question(…) or .ask(…) before calling validate() or exporting to
systems that require it.
