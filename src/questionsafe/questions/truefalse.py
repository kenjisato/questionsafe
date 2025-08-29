from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Self

from .singlechoice import SingleChoice
from ..base._types import FeedbackLike
from ..base._safe import safe_api


@dataclass
class TrueFalse(SingleChoice):
    """True/False specialization of MultiChoice.

    API semantics
    - set_choice_correct(value, feedback=None) rebuilds answers and marks value as correct.
    - set_choice_wrong(value, feedback=None) rebuilds answers and marks value as wrong (opposite correct).
    - Overwrite behavior: subsequent calls overwrite previous answers/feedback unless
      explicitly provided again.
    - The setters are inherited from SingleChoice and accept feedback as
      `Feedback | Text | str | None` (strings are wrapped via Feedback.from_text).

    Attributes
    - qtype: str
        Internal type identifier 'truefalse'.

    Notes
    - validate() enforces exactly two answers with texts 'true' and 'false'.
    - True/False does not support hints or combined feedback in this implementation.
      Those features are disabled via class flags, which also suppresses <penalty> emission.
    """

    qtype: str = "truefalse"
    # Disable features not supported by True/False
    has_hints: bool = False
    has_combined_feedback: bool = False

    def validate(self):
        # Skip mixin penalty validation when hints are disabled by bypassing super().validate()
        # and only calling the base Question.validate (no-op) and then our own checks.
        from ..base._question import Question

        Question.validate(self)
        if len(self.answers) != 2:
            raise ValueError("TrueFalse needs exactly two answers.")
        texts = {a.text.strip().lower() for a in self.answers}
        if texts != {"true", "false"}:
            raise ValueError(
                "TrueFalse answers must be 'true' and 'false' (case-insensitive)."
            )

    def set_choice_correct(
        self, text: str, feedback: Optional[FeedbackLike] = None
    ) -> Self:
        return super().set_choice_correct(text, feedback)

    def set_choice_wrong(
        self, text: str, feedback: Optional[FeedbackLike] = None
    ) -> Self:
        return super().set_choices_wrong(text, feedback=feedback)

    # --- Fluent convenience for common cases ---
    @safe_api
    def set_correct_if_true(self) -> Self:
        """Mark 'true' as correct and 'false' as wrong; returns self for chaining."""
        return self.set_choice_correct("true").set_choice_wrong("false")

    @safe_api
    def set_correct_if_false(self) -> Self:
        """Mark 'false' as correct and 'true' as wrong; returns self for chaining."""
        return self.set_choice_correct("false").set_choice_wrong("true")
