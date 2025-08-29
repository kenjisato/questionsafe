from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional
from abc import ABC

from ._text import Feedback, Text
from ._types import FeedbackLike

AnsNumbering = Literal["none", "abc", "ABCD", "123", "iii", "III"]


@dataclass
class _AnswerBase(ABC):
    """Internal abstract answer base.

    Concrete subclasses should add their own payload fields (e.g., text or value).
    """

    fraction: float
    format: str
    feedback: Optional[Feedback]


class TextAnswer(_AnswerBase):
    """An accepted non-numeric answer with grading and optional feedback."""

    text: str

    def __init__(
        self,
        text: str,
        fraction: float = 0.0,
        format: str = "html",
        feedback: Optional[Feedback] = None,
    ):
        self.text = text
        super().__init__(fraction, format, feedback)

    @classmethod
    def from_text(
        cls,
        val: TextAnswer | Text | str,
        *,
        fraction: float = 0.0,
        feedback: FeedbackLike | None = None,
        format: Optional[str] = None,
    ) -> "TextAnswer":
        """Coerce a value into a TextAnswer.

        - If val is TextAnswer, return as-is.
        - If val is Text, uses its text/format and the given fraction/feedback.
        - If val is str, assumes HTML format unless overridden.
        """
        if isinstance(val, cls):
            return val
        fb = Feedback.from_text(feedback)
        if isinstance(val, Text):
            return cls(
                text=val.text, fraction=float(fraction), format=val.format, feedback=fb
            )
        if isinstance(val, str):
            fmt = format or "html"
            return cls(text=val, fraction=float(fraction), format=fmt, feedback=fb)
        raise TypeError(f"Cannot coerce {type(val)} to TextAnswer")


class NumericalAnswer(_AnswerBase):
    """A numeric answer with optional tolerance and feedback."""

    value: float
    tolerance: Optional[float] = None

    def __init__(
        self,
        value: float,
        tolerance: Optional[float] = None,
        fraction: float = 100.0,
        format: str = "moodle_auto_format",
        feedback: Optional[Feedback] = None,
    ):
        self.value = value
        self.tolerance = tolerance
        super().__init__(fraction, format, feedback)

    @classmethod
    def from_num(
        cls,
        val: NumericalAnswer | float | int,
        *,
        tolerance: Optional[float] = None,
        fraction: float = 100.0,
        feedback: FeedbackLike | None = None,
        format: str = "moodle_auto_format",
    ) -> "NumericalAnswer":
        """Coerce a number into a NumericalAnswer.

        - If val is NumericalAnswer, return as-is.
        - If val is float|int, constructs with provided tolerance/fraction/feedback.
        """
        if isinstance(val, cls):
            return val
        if not isinstance(val, (int, float)):
            raise TypeError(f"Cannot coerce {type(val)} to NumericalAnswer")
        fb = Feedback.from_text(feedback)
        return cls(
            value=float(val),
            tolerance=tolerance,
            fraction=float(fraction),
            format=format,
            feedback=fb,
        )


class Answer:
    """User-facing coercion interface for building answers.

    Example
    - Answer.from_text("Paris", fraction=100)
    - Answer.from_num(3.14, tolerance=0.01)
    """

    # Provide convenient access to concrete classes as attributes
    Text = TextAnswer
    Numerical = NumericalAnswer

    @staticmethod
    def from_text(
        val: TextAnswer | Text | str,
        *,
        fraction: float = 0.0,
        feedback: FeedbackLike | None = None,
        format: Optional[str] = None,
    ) -> TextAnswer:
        return TextAnswer.from_text(
            val, fraction=fraction, feedback=feedback, format=format
        )

    @staticmethod
    def from_num(
        val: NumericalAnswer | float | int,
        *,
        tolerance: Optional[float] = None,
        fraction: float = 100.0,
        feedback: FeedbackLike | None = None,
        format: str = "moodle_auto_format",
    ) -> NumericalAnswer:
        return NumericalAnswer.from_num(
            val,
            tolerance=tolerance,
            fraction=fraction,
            feedback=feedback,
            format=format,
        )
