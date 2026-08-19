# Moodle writer package: context registry and public API
from __future__ import annotations

# Import per-type modules to ensure @ctx.register handlers are registered
from . import category as _category  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import multichoice as _multichoice  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import truefalse as _truefalse  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import shortanswer as _shortanswer  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import numerical as _numerical  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import essay as _essay  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import description as _description  # noqa: F401  # pyright: ignore[reportUnusedImport]
from . import cloze as _cloze  # noqa: F401  # pyright: ignore[reportUnusedImport]

from ._build import render_xml, render_html, write_xml, write_html
from ._versions import parse_version, check_target

__all__ = ["render_xml", "render_html", "write_xml", "write_html", "parse_version", "check_target"]
