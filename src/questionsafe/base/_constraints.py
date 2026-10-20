# _constraints.py
from typing import Iterable, Literal, get_args

# ---- Moodle Constants ----
ALLOWED_FRACTIONS_POS = [
    100.0,
    90.0,
    83.33333,
    80.0,
    75.0,
    70.0,
    66.66667,
    60.0,
    50.0,
    40.0,
    33.33333,
    30.0,
    25.0,
    20.0,
    16.66667,
    14.28571,
    12.5,
    11.11111,
    10.0,
    5.0,
    0.0,
]

ALLOWED_FRACTIONS = set(
    ALLOWED_FRACTIONS_POS + [-v for v in ALLOWED_FRACTIONS_POS if v != 0.0]
)
ALLOWED_PENALTIES = {1.0, 0.5, 0.3333333, 0.25, 0.2, 0.1, 0.0}


def is_allowed(value: float, allowed: set[float], tol: float = 1e-6) -> bool:
    for a in allowed:
        if abs(value - a) <= tol:
            return True
    return False


def uniform_fraction(n: int) -> float:
    """Compute a uniform positive fraction that sums to 100 across n items.

    Raises ValueError if n <= 0.
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    return 100.0 / float(n)


def snap_allowed_positive(value: float, tol: float = 1e-4) -> float | None:
    """Snap value to a canonical allowed positive fraction within tolerance.

    Returns the snapped value if within tol of an allowed positive fraction, else None.
    """
    best = closest_allowed(value, ALLOWED_FRACTIONS_POS)
    if best is not None and best > 0 and abs(best - value) <= tol:
        return best
    return None


def closest_allowed(value: float, candidates: Iterable[float]):
    """Snap to nearest allowed value

    Prefer the closest; on a tie, pick the lower (more lenient) penalty
    """

    from math import inf

    candidates = sorted(candidates, reverse=True)
    best = None
    best_diff = inf
    for a in candidates:
        d = abs(a - value)
        if best is None or d < best_diff or (abs(d - best_diff) <= 1e-9 and a < best):
            best = a
            best_diff = d
    return best


# ---- Scoring rules for wrong choices (after R/exams' exams_eval) ----
ScoringRule = Literal["false2", "false", "true", "all", "none"]
SCORING_RULES: tuple[str, ...] = get_args(ScoringRule)


def wrong_fraction(rule: str, *, n_correct: int, n_wrong: int) -> float:
    """Fraction (in percent) for each wrong choice under a named scoring rule.

    Rules follow R/exams' ``exams_eval``: each wrong choice deducts
    1/max(n_wrong, 2) (``false2``), 1/n_wrong (``false``), 1/n_correct (``true``),
    1 (``all``), or nothing (``none``). The result is snapped to a Moodle-supported
    fraction; raises ValueError when none is close enough.
    """
    shares = {
        "false2": lambda: 1 / max(n_wrong, 2),
        "false": lambda: 1 / n_wrong,
        "true": lambda: 1 / n_correct,
        "all": lambda: 1.0,
        "none": lambda: 0.0,
    }
    if rule not in shares:
        raise ValueError(f"Unknown scoring rule {rule!r}; use one of {SCORING_RULES}")
    share = shares[rule]()
    if share == 0:
        return 0.0
    snapped = snap_allowed_positive(100 * share)
    if snapped is None:
        raise ValueError(
            f"Rule {rule!r} gives -{100 * share:.5f}% per wrong choice, "
            "which is not a supported Moodle fraction."
        )
    return -snapped
