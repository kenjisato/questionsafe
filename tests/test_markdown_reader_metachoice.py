from __future__ import annotations

import textwrap

import pytest


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return str(p)


COFFEE = """
---
type: metachoice
name: Econ/ShiftOrMove
choices:
  INCOME: A rise in consumer income
  TASTES: A shift in consumer tastes toward coffee
  SUBST: An increase in the price of tea
  TECH: An improvement in roasting technology
  INPUT: A fall in the price of raw coffee beans
  WEATHER: A frost that destroys part of the harvest
  PRICE: A change in the market price of coffee
  EXPECT:
    text: News that coffee prices will rise **sharply** next month
    format: markdown
stems:
  DEMAND_SHIFT:
    text: Which of the following shift the *demand* curve for coffee?
    format: markdown
  SUPPLY_SHIFT:
    text: Which of the following shift the *supply* curve for coffee?
    format: markdown
constraints:
  attractor:
    members: [PRICE]
    min: 1
  demand_side:
    members: [INCOME, TASTES, SUBST]
    min: 1
    max: 2
    apply_to: [SUPPLY_SHIFT]
---

# Shift or movement?

Prose outside the fence is commentary; the Reader ignores it.

``` csv
choice,DEMAND_SHIFT,SUPPLY_SHIFT
INCOME,x,
TASTES,x,
SUBST,x,
TECH,,x
INPUT,,x
WEATHER,,x
PRICE,,
EXPECT,x,-
```
"""


def _coffee_python_equivalent(source: str):
    from questionsafe import Text
    from questionsafe.meta import Constraint, MetaChoice

    mc = MetaChoice(name="Econ/ShiftOrMove", source=source)
    mc.set_choices(
        {
            "INCOME": "A rise in consumer income",
            "TASTES": "A shift in consumer tastes toward coffee",
            "SUBST": "An increase in the price of tea",
            "TECH": "An improvement in roasting technology",
            "INPUT": "A fall in the price of raw coffee beans",
            "WEATHER": "A frost that destroys part of the harvest",
            "PRICE": "A change in the market price of coffee",
            "EXPECT": Text("News that coffee prices will rise **sharply** next month", format="markdown"),
        }
    )
    mc.set_constraints({"attractor": Constraint("PRICE", min=1)})
    mc.add_stem(
        "DEMAND_SHIFT",
        Text("Which of the following shift the *demand* curve for coffee?", format="markdown"),
        correct=["INCOME", "TASTES", "SUBST", "EXPECT"],
    )
    mc.add_stem(
        "SUPPLY_SHIFT",
        Text("Which of the following shift the *supply* curve for coffee?", format="markdown"),
        correct=["TECH", "INPUT", "WEATHER"],
        exclude=["EXPECT"],
        constraints={"demand_side": Constraint("INCOME", "TASTES", "SUBST", min=1, max=2)},
    )
    return mc


def test_read_metachoice_matches_python_api(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, COFFEE)
    mc = Reader(p).read_metachoice()
    assert mc.name == "Econ/ShiftOrMove"
    assert mc.source == p

    expected = _coffee_python_equivalent(p)
    got = mc.generate_multichoice(n=4, limit=2, seed=42)
    want = expected.generate_multichoice(n=4, limit=2, seed=42)
    assert list(got) == list(want)


def test_read_metachoice_exclusion_and_constraints_hold(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, COFFEE)
    mc = Reader(p).read_metachoice()
    group = mc.generate_multichoice(n=4, limit=8, seed=7)
    for q in group:
        texts = {str(a.text) for a in q.answers}
        # global attractor: the movement-along-the-curve trap is in every variant
        assert "A change in the market price of coffee" in texts
        if q.name.endswith("SUPPLY_SHIFT"):
            # EXPECT shifts both curves; it must never be sampled here
            assert not any("sharply" in t for t in texts)


def test_read_metachoice_preserves_text_formats(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, COFFEE)
    mc = Reader(p).read_metachoice()
    group = mc.generate_multichoice(n=4, limit=1, seed=1)
    q = next(iter(group))
    assert q.questiontext.format == "markdown"


def test_read_redirects_to_read_metachoice(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, COFFEE)
    with pytest.raises(ValueError, match="read_metachoice"):
        Reader(p).read()


def test_question_type(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, COFFEE)
    assert Reader(p).question_type() == "metachoice"


def test_read_metachoice_rejects_other_types(tmp_path):
    from questionsafe import Reader

    p = _write(
        tmp_path,
        """
        ---
        type: truefalse
        name: TF
        answer: true
        ---
        The sky is blue.
        """,
    )
    with pytest.raises(ValueError, match="truefalse"):
        Reader(p).read_metachoice()


def test_validate_false_skips_template_validation(tmp_path):
    from questionsafe import Reader

    # min > max is representable but invalid at template level
    doc = COFFEE.replace("    min: 1\n    max: 2", "    min: 3\n    max: 2")
    p = _write(tmp_path, doc)
    with pytest.raises(ValueError, match="demand_side"):
        Reader(p).read_metachoice()
    mc = Reader(p).read_metachoice(validate=False)
    assert mc.name == "Econ/ShiftOrMove"


def test_absent_pool_row_is_free_distractor(tmp_path):
    from questionsafe import Reader

    # PRICE has no matrix row in this variant of the file: eligible everywhere
    doc = COFFEE.replace("PRICE,,\n", "")
    p = _write(tmp_path, doc)
    mc = Reader(p).read_metachoice()
    mc.generate_multichoice(n=4, limit=2, seed=42)


def test_uppercase_x_and_quoted_cells(tmp_path):
    from questionsafe import Reader

    doc = COFFEE.replace("INCOME,x,", '"INCOME",X,""')
    p = _write(tmp_path, doc)
    mc = Reader(p).read_metachoice()
    mc.generate_multichoice(n=4, limit=1, seed=1)


MINI_HEAD = """
---
type: metachoice
name: Mini
choices:
  C1: Correct one
  D1: Wrong one
  D2: Wrong two
stems:
  Q1: Pick one
"""


def _mini(constraints: str = "", matrix: str = "choice,Q1\nC1,x\nD1,\nD2,\n") -> str:
    return MINI_HEAD + constraints + "---\n\n```csv\n" + matrix + "```\n"


@pytest.mark.parametrize(
    ("doc", "match"),
    [
        # missing name
        (_mini().replace("name: Mini\n", ""), "name"),
        # missing choices
        (_mini().replace("choices:\n  C1: Correct one\n  D1: Wrong one\n  D2: Wrong two\n", ""), "'choices'"),
        # missing stems
        (_mini().replace("stems:\n  Q1: Pick one\n", ""), "'stems'"),
        # no fence
        (MINI_HEAD + "---\n\nno fence here\n", "exactly one"),
        # two fences
        (_mini() + "\n```csv\nchoice,Q1\n```\n", "exactly one"),
        # unknown stem column
        (_mini(matrix="choice,Q1,Q9\nC1,x,\nD1,,\n"), "unknown stem 'Q9'"),
        # stem missing from header
        (_mini(matrix="choice\nC1\nD1\n"), "'Q1' is missing"),
        # duplicate stem column
        (_mini(matrix="choice,Q1,Q1\nC1,x,x\n"), "[Dd]uplicate stem column 'Q1'"),
        # duplicate choice row
        (_mini(matrix="choice,Q1\nC1,x\nC1,x\n"), "[Dd]uplicate choice row 'C1'"),
        # ragged row
        (_mini(matrix="choice,Q1\nC1,x,extra\nD1,\n"), "expected 2"),
        # unknown choice row
        (_mini(matrix="choice,Q1\nC9,x\nD1,\n"), "unknown choice key 'C9'"),
        # invalid cell token
        (_mini(matrix="choice,Q1\nC1,yes\nD1,\n"), "invalid matrix cell 'yes'"),
        # no correct marked for a stem
        (_mini(matrix="choice,Q1\nC1,\nD1,\n"), "no correct choices"),
        # constraint member not in pool
        (_mini(constraints="constraints:\n  g:\n    members: [NOPE]\n    min: 1\n"), "NOPE"),
        # apply_to unknown stem
        (
            _mini(constraints="constraints:\n  g:\n    members: [D1]\n    max: 1\n    apply_to: [Q9]\n"),
            "unknown stem 'Q9'",
        ),
        # apply_to empty list
        (
            _mini(constraints="constraints:\n  g:\n    members: [D1]\n    max: 1\n    apply_to: []\n"),
            "apply_to",
        ),
        # reserved constraint id
        (
            _mini(constraints="constraints:\n  __excluded__:\n    members: [D1]\n    max: 0\n"),
            "reserved",
        ),
    ],
)
def test_read_metachoice_errors(tmp_path, doc, match):
    from questionsafe import Reader

    p = _write(tmp_path, doc)
    with pytest.raises(ValueError, match=match):
        Reader(p).read_metachoice()
