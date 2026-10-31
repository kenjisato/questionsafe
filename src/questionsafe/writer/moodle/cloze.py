from __future__ import annotations
from ...questions.cloze import Cloze
from ._build import ctx
from .utils import base_question, escape_markdown_math


@ctx.register
def _(q: Cloze):
    d = base_question(q)
    # Escape math in the stem before the gaps go in, so gap texts stay as written
    # (cloze.xml.j2 writes stem_text as is).
    stem = d["stem_text"]
    if d["stem_format"] == "markdown":
        stem = escape_markdown_math(stem)
    d.update(
        {
            "type": "cloze",
            "stem_text": q.compile_text(stem),
        }
    )
    return d
