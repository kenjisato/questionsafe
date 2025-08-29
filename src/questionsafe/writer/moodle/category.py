# Moodle-specific question context builders
from __future__ import annotations
from ...questions import Category
from ._build import ctx


@ctx.register
def _(n: Category):
    # Keep Moodle-specific path normalization here
    import re

    raw = (n.path or "").strip()
    if not raw:
        path = "$course$"
    else:
        first = raw.split("/", 1)[0]
        if re.fullmatch(r"^\$.+\$$", first):
            path = raw
        else:
            path = f"$course$/{raw}"
    return {"type": "category", "path": path}
