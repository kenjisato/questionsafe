# Moodle-specific context for truefalse
from __future__ import annotations
from ...questions.truefalse import TrueFalse
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: TrueFalse):
    d = base_question(q)

    answers = []
    for a in q.answers:
        answers.append(
            {
                "text": (a.text or "").strip().lower(),
                "fraction": a.fraction,
                "answer_format": rt_format(a),
                "feedback_text": rt_text(a.feedback),
                "feedback_format": rt_format(a.feedback),
            }
        )

    # True/False does not support combined feedback in this implementation
    d.update(
        {
            "type": "truefalse",
            "answers": answers,
        }
    )
    return d
