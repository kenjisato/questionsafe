from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Literal

from ..base._answer import TextAnswer, Answer
from ..base._mixins import CombinedFeedbackMixin, MultiTryMixin
from ..base._question import Question
from ..base._text import Feedback, Text
from ._cloze_embed import ClozeEmbeddable


@dataclass
class ShortAnswer(CombinedFeedbackMixin, MultiTryMixin, Question[TextAnswer], ClozeEmbeddable):
    """Short answer question with accepted strings.

    Attributes
    - usecase: int
        1 for case-sensitive matching; 0 for case-insensitive (default).
    - answers: List[Answer]
        Accepted answers with grading fractions and optional feedback.
    - qtype: str
        Internal type identifier 'shortanswer'.
    """

    usecase: int = 0  # 1: case-sensitive, 0: case-insensitive
    answers: List[TextAnswer] = field(default_factory=list)

    qtype: str = "shortanswer"

    def add_answer(
        self,
        answer: TextAnswer | str,
        *,
        fraction: float = 100.0,
        feedback: Optional[Feedback | Text | str] = None,
    ) -> "ShortAnswer":
        """Append an accepted answer.

        Two forms are accepted:
        - add_answer(TextAnswer(...))  # advanced form
        - add_answer(text: str, *, fraction=100.0, feedback=None)  # quickstart form
        """
        if isinstance(answer, TextAnswer):
            ta = answer
        elif isinstance(answer, str):
            ta = Answer.from_text(answer, fraction=fraction, feedback=feedback)
        else:
            raise TypeError("ShortAnswer.add_answer() expects a TextAnswer or a string")
        self.answers.append(ta)
        return self

    # Fluent set_* helpers
    def set_usecase(self, usecase: int | bool) -> "ShortAnswer":
        """Set case sensitivity: 1/True for case-sensitive, 0/False otherwise."""
        self.usecase = int(bool(usecase)) if isinstance(usecase, bool) else int(usecase)
        return self

    def set_answers(self, *answers: TextAnswer) -> "ShortAnswer":
        """Replace the entire set of accepted answers."""
        for a in answers:
            if not isinstance(a, TextAnswer):
                raise TypeError("set_answers expects TextAnswer instances")
        self.answers = list(answers)
        return self

    def validate(self):
        # Base checks (penalty)
        super().validate()
        if not self.answers:
            raise ValueError("ShortAnswer requires at least one accepted <answer>.")
        # Enforce Moodle-supported fraction set (including negatives)
        from ..base._constraints import ALLOWED_FRACTIONS, is_allowed

        for a in self.answers:
            if not is_allowed(float(a.fraction), ALLOWED_FRACTIONS):
                raise ValueError(
                    f"Answer fraction {a.fraction} is not a supported Moodle value."
                )

    # CLOZE embedding method (kept at bottom)
    @ClozeEmbeddable.cloze_precheck
    def cloze(self, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1) -> str:
        parts: list[str] = []
        for i, a in enumerate(self.answers):
            txt = ((a.text) or "").strip()
            if txt == "*" and i != len(self.answers) - 1:
                raise ValueError("Catch-all '*' must be the last answer in ShortAnswer")
            fr = float(a.fraction)
            if txt == "*":
                base = "*"
            else:
                base = ClozeEmbeddable._prefix_by_fraction(fr, txt, include_negative=False)
            fb = a.feedback.text if a.feedback else None  # type: ignore[attr-defined]
            parts.append(ClozeEmbeddable._with_feedback(base, fb))
        kind = "SHORTANSWER_C" if int(getattr(self, "usecase", 0)) else "SHORTANSWER"
        return "{" + f"{self._fmt_weight(weight)}:{kind}:" + "~".join(parts) + "}"
