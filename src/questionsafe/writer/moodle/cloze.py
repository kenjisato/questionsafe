from __future__ import annotations
from ...questions.cloze import Cloze
from ._build import ctx
from .utils import base_question


@ctx.register
def _(q: Cloze):
    d = base_question(q)
    # Render compiled text into stem_text and reset format to html
    d.update(
        {
            "type": "cloze",
            "stem_text": q.compile_text(),
        }
    )
    return d
