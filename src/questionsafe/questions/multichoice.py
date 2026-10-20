# multiplechoice.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Self, Literal

from ..base._answer import TextAnswer, AnsNumbering, Answer
from ..base._text import Feedback, Text
from ..base._mixins import CombinedFeedbackMixin, MultiTryMixin
from ..base._question import Question
from ._cloze_embed import ClozeEmbeddable
from ..base._safe import safe_api
from ..base._constraints import ScoringRule, wrong_fraction


@dataclass
class MultiChoice(CombinedFeedbackMixin, MultiTryMixin, Question[TextAnswer], ClozeEmbeddable):
    """Multiple-choice question (single or multiple selection).

    API semantics
    - set_* methods overwrite/replace existing value(s) with new value(s)
      (e.g., set_choices_correct replaces only positive-fraction answers; set_choices_wrong
      replaces only zero/negative-fraction answers).
    - add_* methods append one value to a list attribute (e.g., add_choice_correct appends
      a new correct choice).

    Notes
    - set_choices_correct distributes 100% uniformly across provided texts (100/N).
    - Use low-level set_answers() for non-uniform fractions or full control.
    - Use set_single_choice(True) to render as radio buttons (single selection) while still allowing
      partial credit across answers if their positive fractions sum to 100.

    Attributes
    - answers: List[Answer]
        Choice options with grading fractions and optional feedback.
    - single_choice: bool
        True for single-answer mode (radio-button UI); False to allow multiple answers.
    - shuffle: bool
        Shuffle the order of answers when presented.
    - labels: AnsNumbering
        One of 'abc' | 'ABCD' | '123' | 'iii' | 'III' | 'none'.
    - combined: CombinedFeedback
        Optional combined feedback shown after answering.
    - qtype: str
        Internal type identifier 'multichoice'.
    """

    answers: List[TextAnswer] = field(default_factory=list)
    single_choice: bool = False
    shuffle: bool = True
    labels: AnsNumbering = "none"

    qtype: str = "multichoice"

    def validate(self):
        # Base checks (penalty)
        super().validate()
        if not self.answers:
            raise ValueError("MultiChoice requires at least one <answer>.")
        if self.single_choice:
            # must have at least one 100% answer
            if not any(abs(float(a.fraction) - 100.0) <= 1e-6 for a in self.answers):
                raise ValueError("Single-choice needs one answer with fraction=100.")
        # Enforce Moodle-supported fraction set (including negatives)
        from ..base._constraints import ALLOWED_FRACTIONS, is_allowed

        for a in self.answers:
            if not is_allowed(float(a.fraction), ALLOWED_FRACTIONS):
                raise ValueError(
                    f"Answer fraction {a.fraction} is not a supported Moodle value."
                )
        # Sum of positive fractions must be 100. Moodle fractions carry five
        # decimals, so snapped uniform splits land slightly off (e.g. three
        # corrects: 3 x 33.33333 = 99.99999); allow that rounding headroom.
        total_positive = sum(max(0.0, float(a.fraction)) for a in self.answers)
        if abs(total_positive - 100.0) > 1e-3:
            raise ValueError(
                f"Sum of positive fractions must be 100; got {total_positive}"
            )

    # Fluent set_* wrappers (aliases)
    def set_labels(self, scheme: AnsNumbering) -> Self:
        self.labels = scheme
        return self

    def set_single_choice(self, on: bool = True) -> Self:
        """Toggle single-answer (radio-button) mode.

        This affects UI presentation and validation rules:
        - When True, a radio-button UI is used. Validation still requires that the sum of
          positive fractions equals 100, but it does not forbid multiple positive fractions.
          This matches Moodle's behavior for multichoice with single=true and allows
          partial credit single-choice questions.
        - When False, multiple answers can be selected (checkbox UI).
        """
        self.single_choice = bool(on)
        return self

    # Quickstart-friendly add_answer: accept a string or a TextAnswer
    def add_answer(
        self,
        answer: TextAnswer | str,
        *,
        fraction: float = 0.0,
        feedback: Optional[Feedback | Text | str] = None,
    ) -> Self:
        """Append an answer.

        Two forms are accepted:
        - add_answer(TextAnswer(...))  # advanced form
        - add_answer(text: str, *, fraction=0.0, feedback=None)  # quickstart form
        """
        if isinstance(answer, TextAnswer):
            ta = answer
        elif isinstance(answer, str):
            ta = Answer.from_text(answer, fraction=fraction, feedback=feedback)
        else:
            raise TypeError("MultiChoice.add_answer() expects a TextAnswer or a string")
        self.answers.append(ta)
        return self

    def set_choice_layout(
        self,
        *,
        labels: Optional[AnsNumbering] = None,
        shuffle: Optional[bool] = None,
        single_choice: Optional[bool] = None,
    ) -> Self:
        if labels is not None:
            self.labels = labels
        if shuffle is not None:
            self.shuffle = bool(shuffle)
        if single_choice is not None:
            self.single_choice = bool(single_choice)
        return self

    # Verbose new API for manipulating choices
    @safe_api
    def add_choice_correct(
        self, text: str, feedback: Optional[Feedback | Text | str] = None
    ) -> Self:
        """Append a correct choice, recalculating uniform fractions when applicable.

        Behavior (colorful/safe contract):
        - If there are no existing correct answers (fraction > 0), add with 100.
        - If there are existing correct answers and their distribution is uniform and sums to 100,
          compute the new uniform fraction = 100 / (n + 1).
            - If this fraction is not in the allowed Moodle set, raise and advise to use low-level API.
            - Otherwise, update existing correct answers to the new uniform fraction and append the new one.
        - If existing corrects are not uniform (or do not sum to 100), raise and advise to use low-level API.
        """
        # Gather existing positives (correct answers)
        positives = [a for a in self.answers if float(a.fraction) > 0]
        if not positives:
            return self.add_answer(Answer.from_text(text, fraction=100, feedback=feedback))

        # Check sum and uniformity
        from ..base._constraints import uniform_fraction, snap_allowed_positive

        total = sum(float(a.fraction) for a in positives)
        if abs(total - 100.0) > 1e-6:
            raise ValueError(
                "Existing correct answers do not sum to 100. Use set_answers() for custom distributions."
            )
        n = len(positives)
        per_now = total / n
        if not all(abs(float(a.fraction) - per_now) <= 1e-6 for a in positives):
            raise ValueError(
                "Existing correct answers are not uniformly distributed. Use set_answers() for custom distributions."
            )

        # New target per-answer fraction
        per_next = uniform_fraction(n + 1)
        per_allowed = snap_allowed_positive(per_next)
        if per_allowed is None:
            raise ValueError(
                "The uniform fraction for the new correct choice is not a supported Moodle value. "
                "Use set_answers() to define an allowed distribution."
            )

        # Update existing positives to per_allowed and append new one
        for a in positives:
            a.fraction = per_allowed  # keep text and feedback
        self.answers.append(Answer.from_text(text, fraction=per_allowed, feedback=feedback))
        return self

    @safe_api
    def add_choice_wrong(
        self,
        text: str,
        *,
        fraction: float = 0.0,
        feedback: Optional[Feedback | Text | str] = None,
    ) -> Self:
        # Guard allowed fractions for safe API
        from ..base._constraints import ALLOWED_FRACTIONS, is_allowed

        if not is_allowed(float(fraction), ALLOWED_FRACTIONS):
            raise ValueError(
                "Provided fraction is not a supported Moodle value. Use set_answers() for custom distributions."
            )
        return self.add_answer(
            Answer.from_text(text, fraction=fraction, feedback=feedback)
        )

    @safe_api
    def set_choices_correct(
        self, *texts: str, feedback: Optional[Feedback | Text | str] = None
    ) -> Self:
        """Replace only positive-fraction answers with new correct ones splitting 100% evenly.

        Behavior
        - Keeps existing answers with fraction <= 0 (wrong/neutral)
        - Replaces existing answers with fraction > 0 using provided texts
        - Each new correct gets fraction = 100 / N (uniform split)
        - If no texts provided, remove all positive-fraction answers
        """
        keep = [a for a in self.answers if float(a.fraction) <= 0]
        if not texts:
            self.answers = keep
            return self
        from ..base._constraints import snap_allowed_positive, uniform_fraction

        per = snap_allowed_positive(uniform_fraction(len(texts)))
        if per is None:
            raise ValueError(
                f"Cannot split 100% uniformly across {len(texts)} correct choices with "
                "Moodle-supported fractions. Use set_answers() for custom distributions."
            )
        new_correct = [
            Answer.from_text(t, fraction=per, feedback=feedback) for t in texts
        ]
        self.answers = keep + new_correct
        return self

    @safe_api
    def set_choices_wrong(
        self,
        *texts: str,
        fraction: float = 0.0,
        feedback: Optional[Feedback | Text | str] = None,
    ) -> Self:
        """Replace only zero/negative-fraction answers with new wrong/partial ones.

        Behavior
        - Keeps existing answers with fraction > 0 (correct)
        - Replaces existing answers with fraction <= 0 using provided texts (default fraction=0.0)
        """
        keep = [a for a in self.answers if float(a.fraction) > 0]
        new_wrong = [
            Answer.from_text(t, fraction=fraction, feedback=feedback) for t in texts
        ]
        self.answers = keep + new_wrong
        return self

    @safe_api
    def set_scoring(self, rule: ScoringRule) -> Self:
        """Set the fraction of every wrong (fraction <= 0) choice by a named rule.

        Rules follow R/exams' ``exams_eval``; see ``wrong_fraction``. Positive
        fractions are kept. ``none`` resets wrong choices to 0.
        """
        wrong = [a for a in self.answers if float(a.fraction) <= 0]
        if not wrong:
            return self
        n_correct = len(self.answers) - len(wrong)
        fr = wrong_fraction(rule, n_correct=n_correct, n_wrong=len(wrong))
        for a in wrong:
            a.fraction = fr
        return self

    def set_shuffle(self, on: bool = True) -> Self:
        """Enable/disable shuffling of answers."""
        self.shuffle = bool(on)
        return self

    def set_answers(self, *answers: TextAnswer) -> Self:
        """Replace the entire choices list with the provided TextAnswer objects."""
        from ..base._answer import TextAnswer as _TA

        for a in answers:
            if not isinstance(a, _TA):
                raise TypeError("set_answers expects TextAnswer instances")
        self.answers = list(answers)
        return self

    # CLOZE embedding method (kept at bottom)
    @ClozeEmbeddable.cloze_precheck
    def cloze(self, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1) -> str:
        """Encode as CLOZE MR token with optional orientation.

        orientation mapping
        - None or 'v': MR (vertical checkboxes)
        - 'h':         MRH (horizontal checkboxes)

        weight must be a nonnegative integer (validated upstream).
        """
        # Map orientation to MULTIRESPONSE variants
        if orientation is None:
            kind = "MR"  # default vertical
        else:
            o = orientation.strip().lower()
            if o in {"v", "vertical"}:
                kind = "MR"
            elif o in {"h", "horizontal"}:
                kind = "MRH"
            else:
                raise ValueError("Invalid orientation. Use None, 'v'|'vertical', or 'h'|'horizontal'.")
        parts = self._tokens_for_text_answers(include_negative=True)
        return "{" + f"{self._fmt_weight(weight)}:{kind}:" + "~".join(parts) + "}"
