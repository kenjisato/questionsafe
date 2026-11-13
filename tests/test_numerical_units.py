"""Numerical units (#16).

Unit options follow Moodle's edit form (question/type/numerical/edit_numerical_form.php):
unit handling (none / optional / graded), and for graded units the penalty, what it is a
fraction of, how the unit is entered, and which side it goes. The writer maps them to the
XML codes that save_unit_options() stores: showunits is the unit role when units are not
graded (3 none, 0 optional) and the input method when they are (0 text, 1 radio,
2 select); unitgradingtype is 0 when not graded, 1 of the response grade, 2 of the
question grade. The Moodle XML format docs describe none of this.
"""
from __future__ import annotations

import textwrap

import pytest
from lxml import etree

from questionsafe import Q, Quiz, Reader, Unit
from questionsafe.base import UnitSpec
from questionsafe.writer.moodle import render_xml


def _xml(q) -> etree._Element:
    root = etree.fromstring(render_xml(Quiz([q])))
    return root.find("question[@type='numerical']")


def _codes(q) -> dict:
    n = _xml(q)
    return {k: n.findtext(k) for k in ("showunits", "unitgradingtype", "unitpenalty", "unitsleft")}


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_defaults_match_moodle():
    # format.php: units without <showunits> import as optional; the edit form's
    # defaults are penalty 0.1 of the response grade, entered as text, on the right.
    q = Q.Numerical(name="N", questiontext="?").add_answer_unit(1100, "g").add_answer_unit(1.1, "kg")
    assert q.units == UnitSpec(units=[Unit("g", 1.0), Unit("kg", 0.001)])
    assert (q.units.handling, q.units.penalty, q.units.penalty_of, q.units.input, q.units.left) == (
        "optional", 0.1, "response", "text", False
    )
    assert _codes(q) == {"showunits": "0", "unitgradingtype": "0", "unitpenalty": "0.1", "unitsleft": "0"}


@pytest.mark.parametrize(
    "options, showunits, unitgradingtype",
    [
        ({"handling": "none"}, "3", "0"),
        ({"handling": "optional"}, "0", "0"),
        ({"handling": "graded"}, "0", "1"),
        ({"handling": "graded", "input": "radio", "penalty_of": "question"}, "1", "2"),
        ({"handling": "graded", "input": "select"}, "2", "1"),
    ],
)
def test_options_map_to_moodle_codes(options, showunits, unitgradingtype):
    q = Q.Numerical(name="N", questiontext="?").add_answer(1).add_units(Unit("m"), **options)
    codes = _codes(q)
    assert (codes["showunits"], codes["unitgradingtype"]) == (showunits, unitgradingtype)


def test_set_unit_options_updates_and_keeps_units():
    q = Q.Numerical(name="N", questiontext="?").add_answer_unit(1, "m")
    q.set_unit_options(handling="graded", penalty=0.3, left=True)
    assert q.units.units == [Unit("m", 1.0)]
    assert _codes(q) == {"showunits": "0", "unitgradingtype": "1", "unitpenalty": "0.3", "unitsleft": "1"}


@pytest.mark.parametrize(
    "bad",
    [{"handling": "required"}, {"input": "dropdown"}, {"penalty_of": "total"}, {"penalty": 1.5}, {"penalty": -0.1}],
)
def test_invalid_options_are_rejected(bad):
    with pytest.raises(ValueError):
        UnitSpec(units=[Unit("m")], **bad)
    with pytest.raises(ValueError):
        Q.Numerical(name="N", questiontext="?").add_answer_unit(1, "m").set_unit_options(**bad)


def test_unit_has_no_fraction():
    # Moodle's <unit> has only multiplier and unit_name; a per-unit fraction was never read.
    with pytest.raises(TypeError):
        Unit("m", 1.0, 100)  # type: ignore[call-arg]
    q = Q.Numerical(name="N", questiontext="?").add_answer(1).add_units(Unit("m"))
    assert _xml(q).find("units/unit/fraction") is None


def test_validate_needs_a_unit_when_units_are_used():
    q = Q.Numerical(name="N", questiontext="?").add_answer(1).set_unit_options(handling="optional")
    with pytest.raises(ValueError, match="unit"):
        q.validate()
    Q.Numerical(name="N", questiontext="?").add_answer(1).set_unit_options(handling="none").validate()


def test_validate_first_unit_is_the_base_unit():
    # The edit form fixes the first unit's multiplier at 1.
    q = Q.Numerical(name="N", questiontext="?").add_answer(1).add_units(Unit("km", 0.001), Unit("m", 1.0))
    with pytest.raises(ValueError, match="multiplier"):
        q.validate()


def test_moodle_code_keywords_are_deprecated():
    with pytest.warns(DeprecationWarning, match="showunits"):
        q = Q.Numerical(name="N", questiontext="?").add_answer(1).add_units(
            Unit("m"), showunits=1, unitgradingtype=2, unitpenalty=0.2
        )
    assert (q.units.handling, q.units.input, q.units.penalty_of, q.units.penalty) == (
        "graded", "radio", "question", 0.2
    )
    with pytest.warns(DeprecationWarning, match="unitsleft"):
        q.set_unit_options(unitsleft=True)
    assert q.units.left is True and q.units.input == "radio"


def test_markdown_units_match_python_api(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N/Units
        answers:
          - answer: 1100
            tolerance: 0
        units:
          - {name: g, multiplier: 1}
          - {name: kg, multiplier: 0.001}
        unit_handling: graded
        unit_penalty: 0.2
        unit_penalty_of: question
        unit_input: select
        units_left: false
        ---
        100g + 1kg = ?
        """,
    )
    q_md = Reader(p).read()
    q_py = (
        Q.Numerical(name="N/Units", questiontext="100g + 1kg = ?")
        .add_answer(1100, tolerance=0)
        .add_units(
            Unit("g", 1), Unit("kg", 0.001),
            handling="graded", penalty=0.2, penalty_of="question", input="select",
        )
    )
    assert q_md.units == q_py.units
    q_md.validate()


def test_markdown_unit_options_default_to_moodle(tmp_path):
    p = _write(
        tmp_path,
        """
        ---
        type: numerical
        name: N
        answer: 1
        units:
          - {name: m}
        ---
        ?
        """,
    )
    assert Reader(p).read().units == UnitSpec(units=[Unit("m", 1.0)])


@pytest.mark.parametrize(
    "extra",
    [
        "units:\n  - {name: m, grade: 1}",  # unknown key in a unit
        "units:\n  units: [{name: m}]\n  showunits: 1",  # the old nested form
        "units:\n  - {name: m}\nunit_handling: required",
        "units:\n  - {name: m}\nunit_input: dropdown",
    ],
)
def test_markdown_rejects_invalid_units(tmp_path, extra):
    p = _write(tmp_path, f"---\ntype: numerical\nname: N\nanswer: 1\n{extra}\n---\n?\n")
    with pytest.raises((ValueError, TypeError)):
        Reader(p).read()
