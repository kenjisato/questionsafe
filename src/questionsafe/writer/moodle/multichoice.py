# Moodle-specific context for multichoice
from __future__ import annotations
from ...questions.multichoice import MultiChoice
from ._build import ctx
from .utils import base_question, rt_text, rt_format


@ctx.register
def _(q: MultiChoice):
    d = base_question(q)
    d.update(
        {
            "type": "multichoice",
            "answers": [
                {
                    "text": a.text,
                    "fraction": a.fraction,
                    "answer_format": "html",
                    "feedback_text": rt_text(a.feedback),
                    "feedback_format": rt_format(a.feedback),
                }
                for a in q.answers
            ],
            "single": bool(getattr(q, "single_choice", getattr(q, "single", False))),
            "shuffleanswers": 1 if bool(getattr(q, "shuffle", getattr(q, "shuffleanswers", True))) else 0,
            "answernumbering": getattr(q, "labels", getattr(q, "answernumbering", "none")),
        }
    )
    return d
