from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from ._constraints import is_allowed, closest_allowed, ALLOWED_PENALTIES
from ._text import Hint, Feedback, Text
from ._types import FeedbackLike


@dataclass(init=False)
class MultiTryMixin:
    """Adds hints support for multi-try/adaptive behavior and penalty control."""

    has_hints: bool = True
    hints: List[Hint] = field(default_factory=list)
    # Penalty per wrong attempt; only relevant for interactive/adaptive questions
    penalty: float = 0.3333333

    def add_hint(
        self,
        hint: Hint | Text | str,
        shownumcorrect: bool | None = None,
        clearwrong: bool | None = None,
    ):
        """Append a single hint with precedence rules for flags.

        Precedence:
        - If `hint` is a Hint: use its flags as-is; ignore parameters.
        - If `hint` is a Text: respect flags found in Text.options; only use parameters
          for flags that are not present in options.
        - If `hint` is a str: use parameters if provided; otherwise defaults apply.
        """
        # Case 1: Already a Hint -> take as-is, ignore params
        if isinstance(hint, Hint):
            h = hint
        # Case 2: A Text (but not a Hint subclass) -> coerce and apply params only if missing
        elif isinstance(hint, Text):
            h = Hint.from_text(hint)
            opts = getattr(hint, "options", {}) or {}
            if "shownumcorrect" not in opts and shownumcorrect is not None:
                h.shownumcorrect = bool(shownumcorrect)
            if "clearwrong" not in opts and clearwrong is not None:
                h.clearwrong = bool(clearwrong)
        # Case 3: Raw string -> coerce and apply params if given, else keep defaults
        elif isinstance(hint, str):
            h = Hint.from_text(hint)
            if shownumcorrect is not None:
                h.shownumcorrect = bool(shownumcorrect)
            if clearwrong is not None:
                h.clearwrong = bool(clearwrong)
        else:
            # Fallback to coercion; should not normally happen given type hints
            h = Hint.from_text(hint)  # type: ignore[arg-type]
        self.hints.append(h)
        return self

    def set_hints(
        self,
        *hints: Hint | Text | str,
        shownumcorrect: bool | None = None,
        clearwrong: bool | None = None,
        penalty: float | str | None = "auto",
    ):
        """Replace the hints list and optionally set the per-try penalty.

        Parameters
        - hints: Hint | Text | str
            Hints to set (replacing existing ones). Flags can be provided via Text.options
            or via the shownumcorrect/clearwrong parameters.
        - shownumcorrect, clearwrong: optional flags applied when not present on the hint.
        - penalty: float | "auto" | None
            If "auto" (default), compute penalty = 1 / (1 + #hints) and snap to nearest
            allowed Moodle penalty. If a float, set exactly (validated). If None, leave
            penalty unchanged.
        """
        self.hints = []
        for h in hints:
            self.add_hint(h, shownumcorrect=shownumcorrect, clearwrong=clearwrong)

        # Optionally set penalty
        if penalty is None:
            return self
        if penalty == "auto":
            n = len(self.hints)
            # 1/(1+n) — when n=0, penalty=1.0; n=1 -> 0.5; n=2 -> ~0.333; n=3 -> 0.25; n=4 -> 0.2
            raw = 1.0 / (1 + max(0, n))
            best = closest_allowed(raw, ALLOWED_PENALTIES)
            try:
                return self.set_penalty(float(best))  # type: ignore[arg-type]
            except Exception:
                # Fallback to current penalty if validation fails for any reason
                return self
        else:
            return self.set_penalty(float(penalty))

    def set_penalty(self, penalty: float):
        """Set the per-try penalty (validated immediately against allowed Moodle values)."""
        self.penalty = float(penalty)
        # Validate immediately to fail fast during construction
        if not is_allowed(float(self.penalty), ALLOWED_PENALTIES, tol=1e-7):
            allowed_str = ", ".join(
                str(p) for p in sorted(ALLOWED_PENALTIES, reverse=True)
            )
            raise ValueError(
                f"penalty must be one of {{{allowed_str}}}; got {self.penalty}"
            )
        return self

    def validate(self) -> None:  # type: ignore[override]
        # Chain to base validation first (if present)
        super_validate = getattr(super(), "validate", None)
        if callable(super_validate):
            super_validate()
        # Validate penalty against Moodle-supported discrete values
        if not is_allowed(float(self.penalty), ALLOWED_PENALTIES, tol=1e-7):
            allowed_str = ", ".join(
                str(p) for p in sorted(ALLOWED_PENALTIES, reverse=True)
            )
            raise ValueError(
                f"penalty must be one of {{{allowed_str}}}; got {self.penalty}"
            )
        return None


@dataclass(init=False)
class CombinedFeedbackMixin:
    """Adds explicit combined feedback fields to a question.

    Fields mirror Moodle combined feedback blocks and are optional.
    """

    has_combined_feedback: bool = True
    feedback_correct: Feedback | Text | str | None = None
    feedback_partiallycorrect: Feedback | Text | str | None = None
    feedback_incorrect: Feedback | Text | str | None = None

    def __post_init__(self):  # type: ignore[override]
        # Coerce any provided fields into Feedback
        if self.feedback_correct is not None:
            self.feedback_correct = Feedback.from_text(self.feedback_correct)
        if self.feedback_partiallycorrect is not None:
            self.feedback_partiallycorrect = Feedback.from_text(
                self.feedback_partiallycorrect
            )
        if self.feedback_incorrect is not None:
            self.feedback_incorrect = Feedback.from_text(self.feedback_incorrect)
        # Cooperate with other mixins/dataclass parents
        super_post = getattr(super(), "__post_init__", None)
        if callable(super_post):
            super_post()

    def set_feedback_correct(self, fb: Optional[FeedbackLike] = None):
        self.feedback_correct = Feedback.from_text(fb)
        return self

    def set_feedback_partiallycorrect(self, fb: Optional[FeedbackLike] = None):
        self.feedback_partiallycorrect = Feedback.from_text(fb)
        return self

    def set_feedback_incorrect(self, fb: Optional[FeedbackLike] = None):
        self.feedback_incorrect = Feedback.from_text(fb)
        return self

    def set_feedback_combined(
        self,
        *,
        correct: Optional[FeedbackLike] = None,
        partiallycorrect: Optional[FeedbackLike] = None,
        incorrect: Optional[FeedbackLike] = None,
    ):
        """Set combined feedback blocks at once."""
        return (
            self.set_feedback_correct(correct)
            .set_feedback_partiallycorrect(partiallycorrect)
            .set_feedback_incorrect(incorrect)
        )
