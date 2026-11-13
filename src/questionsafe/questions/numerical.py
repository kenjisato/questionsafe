# numerical.py
from __future__ import annotations
import warnings
from dataclasses import dataclass, field, replace
from typing import List, Optional, overload, Literal

from ..base._answer import NumericalAnswer, Answer
from ..base._mixins import MultiTryMixin
from ..base._question import Question
from ..base._units import Unit, UnitHandling, UnitInput, UnitPenaltyOf, UnitSpec
from ..base._types import FeedbackLike
from ._cloze_embed import ClozeEmbeddable

# What the deprecated Moodle-code keywords defaulted to: graded, radio, 0.2 of the question grade
_LEGACY_UNIT_DEFAULTS = {"showunits": 1, "unitgradingtype": 2, "unitpenalty": 0.2, "unitsleft": False}
_LEGACY_SPEC_DEFAULTS = {"handling": "graded", "input": "radio", "penalty_of": "question", "penalty": 0.2}


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

    def _legacy_unit_options(self, base: UnitSpec, legacy: dict) -> dict:
        """Map the deprecated Moodle-code keywords onto UnitSpec options."""
        unknown = set(legacy) - set(_LEGACY_UNIT_DEFAULTS)
        if unknown:
            raise TypeError(f"Unexpected keyword arguments: {sorted(unknown)}")
        warnings.warn(
            f"{self.name}: {', '.join(sorted(legacy))} are deprecated; use handling, input, "
            "penalty_of, penalty and left",
            DeprecationWarning,
            stacklevel=3,
        )
        codes = {**base.moodle_codes(), **{k: legacy[k] for k in ("showunits", "unitgradingtype") if k in legacy}}
        options = UnitSpec.options_from_moodle_codes(codes["showunits"], codes["unitgradingtype"])
        if "unitpenalty" in legacy:
            options["penalty"] = legacy["unitpenalty"]
        if "unitsleft" in legacy:
            options["left"] = legacy["unitsleft"]
        return options

    def add_units(
        self,
        *units: Unit,
        handling: UnitHandling = "optional",
        penalty: float = 0.1,
        penalty_of: UnitPenaltyOf = "response",
        input: UnitInput = "text",
        left: bool = False,
        **legacy,
    ) -> "Numerical":
        """Replace the units and their options (see UnitSpec).

        Parameters
        - units: Unit instances, the base unit first, e.g., Unit("m/s"), Unit("km/h", 3.6)
        - handling: "none", "optional" (default), or "graded"
        - penalty, penalty_of, input: for graded units (defaults 0.1, "response", "text")
        - left: show the unit on the left, as in $1.00

        The Moodle-code keywords showunits, unitgradingtype, unitpenalty and unitsleft
        are deprecated.
        """
        for u in units:
            if not isinstance(u, Unit):
                raise TypeError("add_units expects Unit instances as positional arguments")
        options = dict(handling=handling, penalty=penalty, penalty_of=penalty_of, input=input, left=left)
        if legacy:
            options = {**_LEGACY_SPEC_DEFAULTS, **self._legacy_unit_options(UnitSpec(**_LEGACY_SPEC_DEFAULTS), legacy)}
        self.units = UnitSpec(units=list(units), **options)
        return self

    def set_unit_options(
        self,
        *,
        handling: Optional[UnitHandling] = None,
        penalty: Optional[float] = None,
        penalty_of: Optional[UnitPenaltyOf] = None,
        input: Optional[UnitInput] = None,
        left: Optional[bool] = None,
        **legacy,
    ) -> "Numerical":
        """Update unit options, keeping the units; options not given keep their values."""
        given = dict(handling=handling, penalty=penalty, penalty_of=penalty_of, input=input, left=left)
        options = {k: v for k, v in given.items() if v is not None}
        if legacy:
            current = self.units or UnitSpec(**_LEGACY_SPEC_DEFAULTS)
            options = {**self._legacy_unit_options(current, legacy), **options}
        else:
            current = self.units or UnitSpec()
        self.units = replace(current, units=list(current.units), **options)
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
        if self.units is None:
            self.units = UnitSpec()

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

    def set_units(self, *units: Unit, **options) -> "Numerical":
        """Replace the units and their options; same arguments as add_units."""
        return self.add_units(*units, **options)

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
        # Moodle's edit form requires one answer at 100% (fractionsnomax)
        if not any(float(a.fraction) == 100.0 for a in self.answers):
            raise ValueError("Numerical requires one answer worth 100%.")
        # Moodle's edit form: units in use need a unit, and the first one is the base (multiplier 1)
        if self.units is not None and self.units.handling != "none":
            if not self.units.units:
                raise ValueError("Numerical units are used but no unit is given.")
            if float(self.units.units[0].multiplier) != 1.0:
                raise ValueError("The first unit is the base unit; its multiplier must be 1.")

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
