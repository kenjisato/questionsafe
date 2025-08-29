from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

# Allowed sets based on Moodle semantics
_ALLOWED_SHOWUNITS = {
    0,
    1,
    3,
}  # 3: not used, 0: optional, 1: must be right or penalty applied
_ALLOWED_UNITGRADINGTYPE = {
    0,
    1,
    2,
}  # 0: no penalty, 1: fraction response grade, 2: fraction total grade
# Common penalty steps seen in Moodle (match project-wide ALLOWED_PENALTIES)
_ALLOWED_UNIT_PENALTIES = {0.0, 0.1, 0.2, 0.25, 0.3333333, 0.5, 1.0}


def _normalize_fraction(frac: Optional[int]) -> Optional[int]:
    if frac is None:
        return None
    if isinstance(frac, bool):
        # Avoid bools sneaking in as ints
        raise ValueError("Unit.fraction must be an int percentage or None")
    if isinstance(frac, int) and -100 <= frac <= 100:
        return frac
    raise ValueError(f"Unit.fraction must be an integer in [-100, 100], got {frac}")


@dataclass
class Unit:
    """A measurement unit definition for numerical questions."""

    unit_name: str
    multiplier: float = 1.0
    fraction: Optional[int] = None  # Optional per-unit grading fraction

    def __post_init__(self) -> None:
        if not self.unit_name:
            raise ValueError("Unit.unit_name must be non-empty")
        if not isinstance(self.multiplier, (int, float)):
            raise TypeError("Unit.multiplier must be numeric")
        if float(self.multiplier) == 0.0:
            raise ValueError("Unit.multiplier must be non-zero")
        self.fraction = _normalize_fraction(self.fraction)


@dataclass
class UnitSpec:
    """
    Units and unit-handling options

    Attributes
    - units: List[Unit]
        Measurement units with multipliers.
    - showunits: int
        How units are handled: 3) Not used at all, 0) Optional, or 1) must be right or penalty applied.
    - unitgradingtype: int
        0 no penalty, 1 fraction response grade, 2 fraction total grade
    - unitpenalty: float
        Penalty for getting the unit wrong, when they are being graded.
    - unitsleft: bool
        display the unit at left as in $1.00
    """

    units: List[Unit] = field(default_factory=list)
    showunits: int = 0
    unitgradingtype: int = 0
    unitpenalty: float = 0.1
    unitsleft: bool = False

    def __post_init__(self) -> None:
        if self.showunits not in _ALLOWED_SHOWUNITS:
            raise ValueError(
                f"showunits must be one of {_ALLOWED_SHOWUNITS}, got {self.showunits}"
            )
        if self.unitgradingtype not in _ALLOWED_UNITGRADINGTYPE:
            raise ValueError(
                f"unitgradingtype must be one of {_ALLOWED_UNITGRADINGTYPE}, got {self.unitgradingtype}"
            )
        if self.unitpenalty not in _ALLOWED_UNIT_PENALTIES:
            raise ValueError(
                f"unitpenalty must be one of {_ALLOWED_UNIT_PENALTIES}, got {self.unitpenalty}"
            )
        # Ensure all units validate via their own __post_init__
        for u in self.units:
            if not isinstance(u, Unit):
                raise TypeError("units must contain Unit instances")
