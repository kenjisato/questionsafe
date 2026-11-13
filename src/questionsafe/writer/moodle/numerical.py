# Moodle-specific context for numerical
from __future__ import annotations
from typing import List, Dict, Any
from ...questions.numerical import Numerical
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: Numerical):
    d = base_question(q)

    answers: List[Dict[str, Any]] = []
    for a in q.answers:
        answers.append(
            {
                "value": a.value,
                "tolerance": getattr(a, "tolerance", None),
                "fraction": a.fraction,
                "answer_format": "moodle_auto_format",
                "feedback_text": rt_text(getattr(a, "feedback", None)),
                "feedback_format": rt_format(getattr(a, "feedback", None)),
            }
        )

    units: List[Dict[str, Any]] = []
    showunits, unitgradingtype, unitpenalty, unitsleft = 3, 0, 0, False
    if q.units is not None:
        codes = q.units.moodle_codes()
        showunits, unitgradingtype = codes["showunits"], codes["unitgradingtype"]
        unitpenalty, unitsleft = q.units.penalty, q.units.left
        units = [{"unit": u.unit_name, "multiplier": u.multiplier} for u in q.units.units]

    d.update(
        {
            "type": "numerical",
            "answers": answers,
            "units": units,
            "showunits": showunits,
            "unitgradingtype": unitgradingtype,
            "unitpenalty": unitpenalty,
            "unitsleft": unitsleft,
        }
    )
    return d
