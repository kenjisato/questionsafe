# Moodle-specific context for shortanswer
from __future__ import annotations
from ...questions.shortanswer import ShortAnswer
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: ShortAnswer):
    d = base_question(q)
    answers = []
    for a in q.answers:
        answers.append(
            {
                "text": a.text,
                "fraction": a.fraction,
                "answer_format": "moodle_auto_format",
                "feedback_text": rt_text(a.feedback),
                "feedback_format": rt_format(a.feedback),
            }
        )
    d.update(
        {
            "type": "shortanswer",
            "case_sensitive": bool(getattr(q, "case_sensitive", False)),
            "answers": answers,
        }
    )
    return d
