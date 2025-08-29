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
    showunits = 3
    unitgradingtype = 0
    unitpenalty = 0
    unitsleft = False
    if q.units is not None:
        showunits = q.units.showunits
        unitgradingtype = q.units.unitgradingtype
        unitpenalty = q.units.unitpenalty
        unitsleft = q.units.unitsleft
        for u in q.units.units:
            units.append(
                {
                    "unit": u.unit_name,
                    "multiplier": u.multiplier,
                    "fraction": getattr(u, "fraction", None),
                }
            )

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
