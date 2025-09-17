# numerical.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, overload, Literal

from ..base._answer import NumericalAnswer, Answer
from ..base._mixins import MultiTryMixin
from ..base._question import Question
from ..base._units import Unit, UnitSpec
from ..base._types import FeedbackLike
from ._cloze_embed import ClozeEmbeddable


@dataclass
class Numerical(MultiTryMixin, Question[NumericalAnswer], ClozeEmbeddable):
    """Numerical question with numeric answers, tolerances, and units.

    Attributes
    - answers: List[NumericalAnswer]
        One or more numeric answers with optional tolerances.
    - units: Optional[UnitSpec]
        Units and unit handling options, or None to disable units entirely.
    - qtype: str
        Internal type identifier 'numerical'.
    """

    answers: List[NumericalAnswer] = field(default_factory=list)
    units: Optional[UnitSpec] = None
    qtype: str = "numerical"

    # --- Quickstart-friendly API ---
    # Accept either a number or a NumericalAnswer instance
    NumericalAnswerLike = NumericalAnswer | float | int

    @overload
    def add_answer(
        self,
        answer: float | int,
        tolerance: Optional[float] = ...,
        *,
        fraction: float = ...,
        feedback: FeedbackLike | None = ...,
    ) -> "Numerical": ...

    @overload
    def add_answer(
        self,
        answer: NumericalAnswer,
        tolerance: Optional[float] = ...,
        *,
        fraction: float = ...,
        feedback: FeedbackLike | None = ...,
    ) -> "Numerical": ...

    def add_answer(
        self,
        answer: NumericalAnswerLike,
        tolerance: Optional[float] = None,
        *,
        fraction: float = 100.0,
        feedback: FeedbackLike | None = None,
    ) -> "Numerical":
        """Append a numeric answer.

        Two forms are accepted:
        - add_answer(NumericalAnswer(...))  # advanced form
        - add_answer(answer: float, tolerance: float | None = None, *, fraction=100.0, feedback=None)  # quickstart form
        """
        if isinstance(answer, NumericalAnswer):
            ans = answer
        else:
            ans = Answer.from_num(
                answer,
                tolerance=tolerance,
                fraction=fraction,
                feedback=feedback,
            )
        self.answers.append(ans)
        return self

    def _ensure_unitspec(
        self,
        *,
        showunits: Optional[int] = None,
        unitgradingtype: Optional[int] = None,
        unitpenalty: Optional[float] = None,
        unitsleft: Optional[bool] = None,
    ) -> None:
        """Ensure self.units exists; create with sensible defaults if missing.

        Defaults:
        - showunits = 1 (required/graded)
        - unitgradingtype = 2 (fraction of total grade)
        - unitpenalty = 0.2
        - unitsleft = False
        """
        if self.units is None:
            self.units = UnitSpec(
                units=[],
                showunits=1 if showunits is None else showunits,
                unitgradingtype=2 if unitgradingtype is None else unitgradingtype,
                unitpenalty=0.2 if unitpenalty is None else unitpenalty,
                unitsleft=False if unitsleft is None else bool(unitsleft),
            )
        else:
            if showunits is not None:
                self.units.showunits = showunits
            if unitgradingtype is not None:
                self.units.unitgradingtype = unitgradingtype
            if unitpenalty is not None:
                self.units.unitpenalty = unitpenalty
            if unitsleft is not None:
                self.units.unitsleft = bool(unitsleft)

    def add_units(
        self,
        *units: Unit,
        showunits: int = 1,
        unitgradingtype: int = 2,
        unitpenalty: float = 0.2,
        unitsleft: bool = False,
    ) -> "Numerical":
        """Assign a UnitSpec and enable units for this Numerical question.

        Parameters
        - units: one or more Unit instances, e.g., Unit("m/s", 1.0, 100)
        - showunits: 3 not used, 0 optional, 1 required/graded (default 1)
        - unitgradingtype: 0 no penalty, 1 fraction of response grade, 2 fraction of total grade (default 2)
        - unitpenalty: penalty to apply when unit is wrong (must be an allowed value) (default 0.2)
        - unitsleft: if True, display unit to the left (e.g., $1.00)

        Returns
        - self (Numerical) to allow fluent chaining
        """
        # Type check to help users
        for u in units:
            if not isinstance(u, Unit):
                raise TypeError(
                    "add_units expects Unit instances as positional arguments"
                )
        self.units = UnitSpec(
            units=list(units),
            showunits=showunits,
            unitgradingtype=unitgradingtype,
            unitpenalty=unitpenalty,
            unitsleft=unitsleft,
        )
        return self

    def set_unit_options(
        self,
        *,
        showunits: Optional[int] = None,
        unitgradingtype: Optional[int] = None,
        unitpenalty: Optional[float] = None,
        unitsleft: Optional[bool] = None,
    ) -> "Numerical":
        """Set or update global unit-handling options for this question.

        Creates a UnitSpec if missing, preserving existing units.
        """
        existing_units = [] if self.units is None else list(self.units.units)
        self._ensure_unitspec(
            showunits=showunits,
            unitgradingtype=unitgradingtype,
            unitpenalty=unitpenalty,
            unitsleft=unitsleft,
        )
        if self.units is not None and not self.units.units and existing_units:
            self.units.units = existing_units
        return self

    def add_answer_unit(
        self,
        value: float | int,
        unit: str,
        *,
        tolerance: Optional[float] = None,
        fraction: float = 100.0,
        feedback: FeedbackLike | None = None,
    ) -> "Numerical":
        """Add an answer with a unit and infer units/multipliers safely.

        - No grading options here (they are global). Use set_unit_options() to tweak.
        - First call establishes UnitSpec (with defaults) and base unit.
        - Later calls may register additional units by inferring their multiplier
          against the first answer (base). Equivalent values won't add duplicate answers.
        """
        # Ensure UnitSpec exists with sensible defaults
        self._ensure_unitspec()
        # Static typing: after _ensure_unitspec(), units must be present
        assert self.units is not None

        v = float(value)

        # If no units defined yet, establish base unit and base answer
        if not self.units.units:
            self.units.units.append(Unit(unit, 1.0))
            self.add_answer(v, tolerance, fraction=fraction, feedback=feedback)
            return self

        # Units already defined
        base_present = bool(self.answers)
        base_value = float(self.answers[0].value) if base_present else None

        # Get multiplier for provided unit or infer it
        name_to_unit = {u.unit_name: u for u in self.units.units}
        if unit in name_to_unit:
            m = float(name_to_unit[unit].multiplier)
        else:
            if not base_present:
                # Ambiguous: cannot infer multiplier without a base answer
                raise ValueError(
                    "Cannot infer multiplier for new unit without a base answer. "
                    "Define units explicitly with add_units()/set_units(), or call "
                    "add_answer_unit() first using the intended base unit."
                )
            if v == 0.0:
                raise ValueError(
                    "Cannot infer multiplier from a zero value. Define units explicitly via add_units()/set_units()."
                )
            assert base_value is not None
            m = v / base_value  # base * m == value
            self.units.units.append(Unit(unit, m))

        # Convert given value into base units
        converted = v / m

        if not base_present:
            # First answer while units existed (base must have been pre-defined externally)
            self.add_answer(converted, tolerance, fraction=fraction, feedback=feedback)
            return self

        # Avoid duplicate equivalent answers
        assert base_value is not None
        if abs(converted - float(base_value)) > 1e-9:
            self.add_answer(converted, tolerance, fraction=fraction, feedback=feedback)
        return self

    # Fluent set_* helpers
    def set_answer(
        self,
        value: float,
        tolerance: Optional[float] = None,
        *,
        fraction: float = 100.0,
        feedback: FeedbackLike | None = None,
    ) -> "Numerical":
        """Replace answers with a single numeric answer (quickstart convenience)."""
        self.answers = []
        return self.add_answer(value, tolerance, fraction=fraction, feedback=feedback)

    def set_answers(self, *answers: NumericalAnswer) -> "Numerical":
        """Replace the list of numeric answers."""
        from ..base._answer import NumericalAnswer as _NA

        for a in answers:
            if not isinstance(a, _NA):
                raise TypeError("set_answers expects NumericalAnswer instances")
        self.answers = list(answers)
        return self

    def set_units(
        self,
        *units: Unit,
        showunits: int = 1,
        unitgradingtype: int = 2,
        unitpenalty: float = 0.2,
        unitsleft: bool = False,
    ) -> "Numerical":
        """Assign a UnitSpec via units and options (thin wrapper around add_units)."""
        return self.add_units(
            *units,
            showunits=showunits,
            unitgradingtype=unitgradingtype,
            unitpenalty=unitpenalty,
            unitsleft=unitsleft,
        )

    def validate(self):
        # Base checks (penalty)
        super().validate()
        if not self.answers:
            raise ValueError("Numerical requires at least one \u003canswer\u003e.")
        # tolerances are optional; Moodle treats missing tolerance as exact match
        # Enforce Moodle-supported fraction set (including negatives) for answer grades
        from ..base._constraints import ALLOWED_FRACTIONS, is_allowed

        for a in self.answers:
            if not is_allowed(float(a.fraction), ALLOWED_FRACTIONS):
                raise ValueError(
                    f"Answer fraction {a.fraction} is not a supported Moodle value."
                )
        # UnitSpec validates itself; nothing else to do here

    # CLOZE embedding method (kept at bottom)
    @ClozeEmbeddable.cloze_precheck
    def cloze(self, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1) -> str:
        def fmt_value(val: float) -> str:
            return f"{float(val):.15g}"

        def fmt_tol(tol: float | None) -> str:
            return ":" + f"{float(tol):.15g}" if tol is not None else ""

        parts: list[str] = []
        for a in self.answers:
            base = fmt_value(a.value) + fmt_tol(getattr(a, "tolerance", None))  # type: ignore[arg-type]
            fr = float(a.fraction)
            prefixed = ClozeEmbeddable._prefix_by_fraction(fr, base, include_negative=False)
            fb_text = a.feedback.text if a.feedback else None  # type: ignore[attr-defined]
            parts.append(ClozeEmbeddable._with_feedback(prefixed, fb_text))
        return "{" + f"{self._fmt_weight(weight)}:NUMERICAL:" + "~".join(parts) + "}"
