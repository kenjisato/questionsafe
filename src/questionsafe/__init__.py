from . import questions as questions
from .quiz import Quiz

# Re-export common types for simpler imports
from .base import Hint, Feedback, Unit
from .base import Text  # new user-facing rich text value
from .base._answer import Answer  # user-facing coercion interface

# Re-export top-level helpers for convenience: questionsafe.render_xml(...), questionsafe.write_xml(...)
from .writer import render_xml, render_html, write_xml, write_html
from .base import list_safe_apis  # surfaced for convenience

# Short alias for the questions facade
Q = questions  # questions facade (e.g., Q.MultiChoice)

# Import Reader after Q is defined to avoid circular import during package init
from .importers import Reader  # noqa: E402  Markdown Reader (MD -> Question)
__all__ = [
    # facades
    "Q",
    "Quiz",
    # common types and interfaces
    "Hint",
    "Feedback",
    "Text",
    "Unit",
    "Answer",
    # helpers
    "render_xml",
    "render_html",
    "write_xml",
    "write_html",
    # safe API tooling
    "list_safe_apis",
    # importers
    "Reader",
]
