# singlechoice.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Self, Literal

from .multichoice import MultiChoice
from ..base._types import FeedbackLike
from ..base._answer import Answer
from ._cloze_embed import ClozeEmbeddable
from ..base._safe import safe_api


@dataclass
class SingleChoice(MultiChoice, ClozeEmbeddable):
    """Single-choice question.

    Semantics
    - Represents the single-answer variant of a choice question.
    - Enforces single_choice=True and keeps the same Moodle qtype ("multichoice").
    - Validation rules inherited from MultiChoice already enforce that the sum of
      positive fractions is 100, which with single_choice=True implies exactly one 100% answer.

    Caveat
    - Moodle allows multichoice with single=true to include multiple answers with
      positive fractions that sum to 100 (enabling partial credit in a radio-button UI).
      This SingleChoice class deliberately prohibits multiple positive fractions to reduce
      the chance of confusing questions. If you want radio-button input with partial credit,
      use MultiChoice with explicit set_answers(...) and then call set_single_choice(True).
      Example: MultiChoice(...).set_answers(...).set_single_choice()
    """

    single_choice: bool = True
    # Disable combined feedback for SingleChoice explicitly
    has_combined_feedback: bool = False

    def validate(self):
        # Run base validations (penalty checks, allowed fractions, etc.)
        super().validate()
        # Enforce exactly one positive-fraction answer and that it is 100%
        positives = [a for a in self.answers if float(getattr(a, "fraction", 0.0)) > 0]
        if len(positives) != 1 or abs(float(positives[0].fraction) - 100.0) > 1e-6:
            raise ValueError(
                "SingleChoice must have exactly one correct answer with fraction=100 and no other positive fractions."
            )

    @safe_api
    def set_choice_correct(
        self, text: str, feedback: Optional[FeedbackLike] = None
    ) -> Self:
        """Set exactly one correct answer (fraction=100), replacing any existing corrects.

        Keeps existing wrong/neutral answers (fraction <= 0). If a wrong with the same text
        exists, it is removed to avoid duplicate labels.
        """
        t = text.strip()
        # Keep only non-positive answers with different text to avoid duplicates
        keep = [
            a for a in self.answers if float(getattr(a, "fraction", 0.0)) <= 0 and a.text.strip() != t
        ]
        new_correct = Answer.from_text(t, fraction=100, feedback=feedback)
        self.answers = keep + [new_correct]
        return self

    # Guard colorful API: prevent adding multiple corrects via add_choice_correct
    @safe_api
    def add_choice_correct(self, text: str, feedback: Optional[FeedbackLike] = None) -> Self:
        if any(abs(float(getattr(a, "fraction", 0.0)) - 100.0) <= 1e-6 for a in self.answers):
            raise ValueError(
                "SingleChoice already has a correct answer (fraction=100). Use add_answer() for advanced usage."
            )
        # Delegate to MultiChoice implementation for actual append
        return super().add_choice_correct(text, feedback)

    # CLOZE embedding method (kept at bottom)
    @ClozeEmbeddable.cloze_precheck
    def cloze(self, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1) -> str:
        """Encode as CLOZE MC token with optional orientation.

        orientation mapping
        - None: MC (dropdown)
        - 'v':   MCV (vertical radios)
        - 'h':   MCH (horizontal radios)

        weight must be a nonnegative integer (validated upstream).
        """
        # Map human-friendly orientation to CLOZE token kind
        kind = None
        if orientation is None:
            kind = "MC"  # dropdown
        else:
            o = orientation.strip().lower()
            if o in {"v", "vertical"}:
                kind = "MCV"
            elif o in {"h", "horizontal"}:
                kind = "MCH"
            else:
                raise ValueError("Invalid orientation. Use None, 'v'|'vertical', or 'h'|'horizontal'.")
        parts = self._tokens_for_text_answers(include_negative=False)
        return "{" + f"{self._fmt_weight(weight)}:{kind}:" + "~".join(parts) + "}"
