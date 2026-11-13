from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal

# Option values follow Moodle's numerical edit form (edit_numerical_form.php).
# The Moodle XML format docs do not describe <showunits>/<unitgradingtype>; the codes
# below come from qtype_numerical's constants and save_unit_options().
UnitHandling = Literal["none", "optional", "graded"]
UnitInput = Literal["text", "radio", "select"]
UnitPenaltyOf = Literal["response", "question"]

_SHOWUNITS_UNGRADED = {"none": 3, "optional": 0}  # UNITNONE, UNITOPTIONAL
_SHOWUNITS_GRADED = {"text": 0, "radio": 1, "select": 2}  # UNITINPUT, UNITRADIO, UNITSELECT
_UNITGRADINGTYPE = {"response": 1, "question": 2}  # UNITGRADEDOUTOFMARK, UNITGRADEDOUTOFMAX


@dataclass
class Unit:
    """A unit for numerical answers.

    `multiplier` converts from the base unit: a value in this unit is the value in the
    base unit times the multiplier (base g: kg has multiplier 0.001). The base unit, with
    multiplier 1, comes first.
    """

    unit_name: str
    multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not self.unit_name:
            raise ValueError("Unit.unit_name must be non-empty")
        if isinstance(self.multiplier, bool) or not isinstance(self.multiplier, (int, float)):
            raise TypeError("Unit.multiplier must be numeric")
        if float(self.multiplier) == 0.0:
            raise ValueError("Unit.multiplier must be non-zero")


@dataclass
class UnitSpec:
    """Units and how Moodle handles them, as on Moodle's edit form.

    Attributes
    - units: the base unit first, then the others.
    - handling: "none" (units not used), "optional" (a unit, if given, converts the
      response), or "graded" (the unit must be given and is graded).
    - penalty: 0-1, deducted for a wrong unit (graded only).
    - penalty_of: "response" (fraction of the response grade) or "question"
      (fraction of the question grade) (graded only).
    - input: "text", "radio", or "select": how the student gives the unit (graded only).
    - left: show the unit on the left, as in $1.00.

    Defaults are Moodle's: units imported without options are optional, and the edit
    form defaults to penalty 0.1 of the response grade, entered as text, on the right.
    """

    units: List[Unit] = field(default_factory=list)
    handling: UnitHandling = "optional"
    penalty: float = 0.1
    penalty_of: UnitPenaltyOf = "response"
    input: UnitInput = "text"
    left: bool = False

    def __post_init__(self) -> None:
        for name, value, allowed in (
            ("handling", self.handling, ("none", "optional", "graded")),
            ("penalty_of", self.penalty_of, tuple(_UNITGRADINGTYPE)),
            ("input", self.input, tuple(_SHOWUNITS_GRADED)),
        ):
            if value not in allowed:
                raise ValueError(f"Unit {name} must be one of {allowed}, got {value!r}")
        if not 0.0 <= float(self.penalty) <= 1.0:
            raise ValueError(f"Unit penalty must be between 0 and 1, got {self.penalty}")
        self.left = bool(self.left)
        for u in self.units:
            if not isinstance(u, Unit):
                raise TypeError("units must contain Unit instances")

    def moodle_codes(self) -> dict:
        """The <showunits> and <unitgradingtype> values Moodle stores for these options."""
        if self.handling == "graded":
            return {
                "showunits": _SHOWUNITS_GRADED[self.input],
                "unitgradingtype": _UNITGRADINGTYPE[self.penalty_of],
            }
        return {"showunits": _SHOWUNITS_UNGRADED[self.handling], "unitgradingtype": 0}

    @staticmethod
    def options_from_moodle_codes(showunits: int, unitgradingtype: int) -> dict:
        """Inverse of moodle_codes(); the input and penalty_of only exist for graded units."""
        if unitgradingtype == 0:
            handling = {v: k for k, v in _SHOWUNITS_UNGRADED.items()}.get(showunits)
            if handling is None:
                raise ValueError(f"showunits must be 3 or 0 when units are not graded, got {showunits}")
            return {"handling": handling}
        input_ = {v: k for k, v in _SHOWUNITS_GRADED.items()}.get(showunits)
        penalty_of = {v: k for k, v in _UNITGRADINGTYPE.items()}.get(unitgradingtype)
        if input_ is None or penalty_of is None:
            raise ValueError(f"Invalid showunits/unitgradingtype: {showunits}/{unitgradingtype}")
        return {"handling": "graded", "input": input_, "penalty_of": penalty_of}
