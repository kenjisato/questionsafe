from __future__ import annotations
from typing import Any, Callable

SAFE_PREFIX = "[SAFE] "


def safe_api(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method/function as part of the safe (colorful) API.

    Effects
    - Attaches an attribute `_safe_api = True` for introspection.
    - Prefixes the docstring with "[SAFE] " if not already present so IDEs/help() show it.
    """
    fn._safe_api = True
    doc = getattr(fn, "__doc__", None)
    if doc:
        trimmed = doc.lstrip()
        if not trimmed.startswith(SAFE_PREFIX):
            fn.__doc__ = SAFE_PREFIX + doc
    else:
        fn.__doc__ = SAFE_PREFIX
    return fn


def list_safe_apis(obj: Any) -> list[tuple[str, str | None]]:
    """List (name, doc) for callables on obj marked as safe via @safe_api.

    - If obj is a class or module, scans its attributes.
    - If obj is an instance, scans its type.
    """
    target = obj if hasattr(obj, "__dict__") else type(obj)
    results: list[tuple[str, str | None]] = []
    for name in dir(target):
        try:
            attr = getattr(target, name)
        except Exception:
            continue
        if callable(attr) and getattr(attr, "_safe_api", False):
            results.append((name, getattr(attr, "__doc__", None)))
    return sorted(results, key=lambda x: x[0])
