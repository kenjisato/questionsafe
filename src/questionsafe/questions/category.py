# category.py
from __future__ import annotations
from dataclasses import dataclass

from ..base._question import QuestionText, Question


@dataclass(init=False)
class Category(Question):
    """A category marker that can appear alongside questions.

    Implements Question in order to be treated as a question-like object,
    but only 'path' is meaningful for rendering. Other Question fields are
    initialized with safe defaults.
    """

    path: str  # e.g. $course$/MyCourse/Week1
    qtype: str = "category"

    def __init__(self, path: str) -> None:
        # set our specific field first
        self.path = path
        # initialize Question with minimal placeholders
        super().__init__(name="", questiontext=QuestionText(""))

    def __str__(self) -> str:
        """Return a concise representation of this category marker."""
        return f"Category('{self.path}')"

    def validate(self) -> None:
        """Validate that Category.path is non-empty after stripping whitespace."""
        raw = (self.path or "").strip()
        if not raw:
            raise ValueError("Category.path must not be empty")
        return None

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation."""
        return f"<Category path={self.path!r}>"
