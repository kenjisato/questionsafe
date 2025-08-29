from pathlib import Path

import pytest

from questionsafe.base._units import Unit, UnitSpec
from questionsafe.writer.moodle._templating import make_env
from questionsafe.writer.moodle._build import render_html, to_context
from questionsafe import Q, Quiz
from questionsafe.base import QuestionText


def test_unit_validation_ok_and_fraction_normalization():
    u = Unit(unit_name="m", multiplier=1, fraction=0)
    assert u.unit_name == "m"
    assert isinstance(u.multiplier, float) or isinstance(u.multiplier, int)
    # fraction stays as int in range
    assert u.fraction == 0

    # None allowed
    Unit(unit_name="cm", multiplier=0.01, fraction=None)


def test_unit_validation_errors():
    with pytest.raises(ValueError):
        Unit(unit_name="", multiplier=1)
    with pytest.raises(TypeError):
        Unit(unit_name="m", multiplier="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Unit(unit_name="m", multiplier=0)
    with pytest.raises(ValueError):
        Unit(unit_name="m", multiplier=1, fraction=101)
    with pytest.raises(ValueError):
        Unit(unit_name="m", multiplier=1, fraction=-101)
    # bool is a subclass of int -> explicitly rejected
    with pytest.raises(ValueError):
        Unit(unit_name="m", multiplier=1, fraction=True)  # type: ignore[arg-type]


def test_unitspec_validation_ok_and_enums():
    spec = UnitSpec(
        units=[Unit("m", 1.0), Unit("cm", 0.01)],
        showunits=1,
        unitgradingtype=2,
        unitpenalty=0.25,
        unitsleft=True,
    )
    assert len(spec.units) == 2
    assert spec.showunits in {0, 1, 3}
    assert spec.unitgradingtype in {0, 1, 2}
    assert spec.unitpenalty in {0.0, 0.1, 0.2, 0.25, 0.3333333, 0.5, 1.0}


def test_unitspec_rejects_invalid_values_and_types():
    with pytest.raises(ValueError):
        UnitSpec(showunits=42)
    with pytest.raises(ValueError):
        UnitSpec(unitgradingtype=5)
    with pytest.raises(ValueError):
        UnitSpec(unitpenalty=0.3)
    with pytest.raises(TypeError):
        UnitSpec(units=["m"])  # type: ignore[list-item]


# templating filters and behaviors


def test_make_env_filters_slug_numscheme_xmlbool_and_cdata(tmp_path: Path):
    env = make_env(user_dir=None, kind="xml")
    # slug
    f_slug = env.filters["slug"]
    assert f_slug(" Hello, World!  ") == "hello-world"
    assert f_slug("!!!") == "category"  # fallback when nothing remains
    # numscheme
    f_num = env.filters["numscheme"]
    assert f_num("ABCD") == "ABCD"
    assert f_num("invalid") == "none"
    assert f_num(None) == "none"
    # xmlbool
    f_xmlbool = env.filters["xmlbool"]
    assert f_xmlbool(True) == "true"
    assert f_xmlbool("1") == "true"
    assert f_xmlbool("TRUE") == "true"
    assert f_xmlbool(False) == "false"
    assert f_xmlbool("no") == "false"
    # cdata
    f_cdata = env.filters["cdata"]
    assert f_cdata(None) == "<![CDATA[]]>"
    assert f_cdata("x<y>") == "<![CDATA[x<y>]]>"


def test_render_html_title_selection_from_quiz_title():
    qz = Quiz()
    qz.title = "My Quiz"
    # No questions needed for this behavior; just ensure HTML renders and title used
    html = render_html(qz)  # title None -> should pick qz.title
    assert "My Quiz" in html


def test_to_context_accepts_iterable_and_base_question_defaults():
    # Build minimal TrueFalse to exercise base_question normalization
    t = Q.TrueFalse(name="T", questiontext=QuestionText("T?"))
    # no idnumber set -> base_question should normalize to empty string
    cs = to_context([t])
    assert isinstance(cs, list) and len(cs) == 1
    n = cs[0]
    # required keys
    for key in ("name", "stem_text", "stem_format", "defaultgrade", "idnumber", "type"):
        assert key in n
    assert n["idnumber"] == ""
