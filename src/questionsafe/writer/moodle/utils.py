# Moodle-specific helpers
from __future__ import annotations
from typing import Any, Dict
from .._common import rt_text, rt_format  # use common helpers


def base_question(q: Any) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "name": q.name,
        "stem_text": rt_text(q.questiontext),
        "stem_format": rt_format(q.questiontext),
        "defaultgrade": q.defaultgrade,
        "tags": list(getattr(q, "tags", []) or []),
        "idnumber": (getattr(q, "idnumber", None) or ""),
    }

    fb_g = getattr(q, "feedback_general", None)
    d.update(
        {
            "feedback_general_text": rt_text(fb_g),
            "feedback_general_format": rt_format(fb_g),
        }
    )

    has_hints = getattr(q, "has_hints", False)
    if has_hints:
        d.update(
            {
                "has_hints": has_hints,
                "penalty": getattr(q, "penalty", 0.3333333),
                "hints": [
                    {
                        "text": rt_text(h),
                        "format": rt_format(h),
                        "shownumcorrect": getattr(h, "shownumcorrect", False),
                        "clearwrong": getattr(h, "clearwrong", False),
                    }
                    for h in (getattr(q, "hints", []) or [])
                ],
            }
        )

    has_combined = getattr(q, "has_combined_feedback", False)
    if has_combined:
        fb_c = getattr(q, "feedback_correct", None)
        fb_p = getattr(q, "feedback_partiallycorrect", None)
        fb_i = getattr(q, "feedback_incorrect", None)
        d.update(
            {
                "has_combined_feedback": has_combined,
                "feedback_correct_text": rt_text(fb_c),
                "feedback_correct_format": rt_format(fb_c),
                "feedback_partially_text": rt_text(fb_p),
                "feedback_partially_format": rt_format(fb_p),
                "feedback_incorrect_text": rt_text(fb_i),
                "feedback_incorrect_format": rt_format(fb_i),
            }
        )

    return d
