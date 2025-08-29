# Moodle-specific context for description
from __future__ import annotations
from ...questions.description import Description
from ._build import ctx
from .utils import base_question


@ctx.register
def _(q: Description):
    d = base_question(q)
    d.update(
        {
            "type": "description",
        }
    )
    return d
