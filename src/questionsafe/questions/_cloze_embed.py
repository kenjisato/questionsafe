from __future__ import annotations
from typing import Literal, Optional

class ClozeEmbeddable:
    """Mixin indicating a question can be embedded in a CLOZE.

    Child classes must implement:
        def cloze(self, *, orientation: Optional[str] = None, weight: int = 1) -> str
    """

    @staticmethod
    def _validate_weight(weight: int) -> int:
        """Validate CLOZE item weight: must be a nonnegative integer (bool not allowed)."""
        if not isinstance(weight, int) or isinstance(weight, bool):
            raise TypeError("weight must be an integer")
        if weight < 0:
            raise ValueError("weight must be a nonnegative integer")
        return weight

    @staticmethod
    def _fmt_weight(w: int) -> str:
        return str(int(w))

    # Common validator decorator for cloze() methods
    @staticmethod
    def cloze_precheck(func):  # type: ignore[no-untyped-def]
        from functools import wraps
        # On raw text, forbid these combinations (including '~%')
        bad_raw = ("%#", "%~", "%}", "=#", "=%", "=}", "~#", "~%", "~}")

        @wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            self = args[0]
            weight = kwargs.get("weight", 1)
            ClozeEmbeddable._validate_weight(weight)
            for a in getattr(self, "answers", []):
                fb = getattr(a, "feedback", None)
                fb_text = getattr(fb, "text", None) if fb is not None else None
                # Text-based questions: enforce non-empty text and scan for bad sequences
                if hasattr(a, "text"):
                    txt = (getattr(a, "text", "") or "").strip()
                    if txt == "":
                        raise ValueError("Answer text must not be empty.")
                    for b in bad_raw:
                        if b in txt or (fb_text and b in fb_text):
                            raise ValueError(
                                f"Invalid CLOZE token sequence contains '{b}'. Ensure non-empty answers and feedback."
                            )
                else:
                    # Non-text answers (e.g., Numerical): only validate feedback, not value
                    for b in bad_raw:
                        if fb_text and b in fb_text:
                            raise ValueError(
                                f"Invalid CLOZE token sequence contains '{b}'. Ensure feedback does not contain reserved sequences."
                            )
            return func(*args, **kwargs)

        return wrapper

    # ---------- Shared helpers for building CLOZE tokens ----------
    @staticmethod
    def _prefix_by_fraction(fr: float, text: str, *, include_negative: bool = False) -> str:
        """Return token with '=' for 100%, '%f%' for partials (and negatives if requested)."""
        if fr > 0 and abs(fr - 100.0) <= 1e-6:
            return "=" + text
        if fr > 0 or (include_negative and fr != 0):
            return f"%{fr}%" + text
        return text

    @staticmethod
    def _with_feedback(token: str, feedback_text: Optional[str]) -> str:
        return token + ("#" + feedback_text if feedback_text else "")

    def _tokens_for_text_answers(self, *, include_negative: bool = False) -> list[str]:  # type: ignore[override]
        parts: list[str] = []
        for a in getattr(self, "answers", []):
            txt = (getattr(a, "text", "") or "").strip()
            fr = float(getattr(a, "fraction", 0.0))
            fb = getattr(a, "feedback", None)
            fb_text = getattr(fb, "text", None) if fb is not None else None
            base = ClozeEmbeddable._prefix_by_fraction(fr, txt, include_negative=include_negative)
            parts.append(ClozeEmbeddable._with_feedback(base, fb_text))
        return parts

    def cloze(self, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1) -> str:
        raise NotImplementedError
