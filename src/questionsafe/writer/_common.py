# Common helpers for writer backends (LMS-agnostic)
from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, List, Dict, Callable


DefQuestions = Any


def to_context(
    obj: DefQuestions, ctx: Callable[[object], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Normalize obj to a list of context dicts using the provided ctx registry.

    Accepts either:
    - A Quiz-like object with a .questions attribute
    - An iterable of question-like objects
    - A single question-like object (singleton)
    """
    if hasattr(obj, "questions"):
        iterable = obj.questions
    else:
        # Treat non-iterables (and strings) as a singleton
        if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
            iterable = obj
        else:
            iterable = [obj]
    return [ctx(q) for q in iterable]  # type: ignore[arg-type]


def title_of(obj: object, default: str = "Preview") -> str:
    try:
        t = getattr(obj, "title", None)
        if t is not None:
            return str(t)
    except Exception:
        pass
    return default


def write_bytes(data: bytes, path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def write_text(s: str, path: Path | str, *, encoding: str = "utf-8") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding=encoding)
    return p


def rt_text(rt: Any) -> str:
    return "" if rt is None else getattr(rt, "text", str(rt))


def rt_format(rt: Any) -> str:
    return "html" if rt is None else getattr(rt, "format", "html")
