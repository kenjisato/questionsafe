from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, TypeVar, Type


@dataclass
class Text:
    """Rich text value with an explicit format and optional options.

    Attributes
    - text: str
        The content (typically HTML).
    - format: str
        One of 'html', 'moodle_auto_format', 'plain_text', 'markdown' (default 'html').
    - options: Mapping[str, Any]
        Additional options specific to the usage site (e.g., hint flags).
    """

    text: str
    format: str = "html"
    options: Mapping[str, Any] = field(default_factory=dict)


TGI = TypeVar("TGI", bound="GraderInfo")
TH = TypeVar("TH", bound="Hint")
TFB = TypeVar("TFB", bound="Feedback")


@dataclass
class GraderInfo(Text):
    """
    <graderinfo> ... </graderinfo> (essay)
    """

    @classmethod
    def from_text(cls: Type[TGI], val: GraderInfo | Text | str) -> TGI:
        if isinstance(val, cls):
            return val
        if isinstance(val, Text):
            return cls(text=val.text, format=val.format, options=val.options)
        if isinstance(val, str):
            return cls(text=val, format="html")
        raise TypeError(f"Cannot coerce {type(val)} to GraderInfo")


@dataclass
class Hint(Text):
    """
    <hint> ... </hint> with optional flags.
    """

    shownumcorrect: bool = False
    clearwrong: bool = False

    @classmethod
    def from_text(cls: Type[TH], val: Hint | Text | str) -> TH:
        if isinstance(val, cls):
            return val
        if isinstance(val, Text):
            shownumcorrect = bool(
                getattr(val, "options", {}).get("shownumcorrect", False)
            )
            clearwrong = bool(getattr(val, "options", {}).get("clearwrong", False))
            return cls(
                text=val.text,
                format=val.format,
                options=val.options,
                shownumcorrect=shownumcorrect,
                clearwrong=clearwrong,
            )
        if isinstance(val, str):
            return cls(text=val, format="html")
        raise TypeError(f"Cannot coerce {type(val)} to Hint")


@dataclass
class Feedback(Text):
    """
    <feedback> ... </feedback>
    """

    @classmethod
    def from_text(cls: Type[TFB], val: Feedback | Text | str | None) -> TFB | None:
        if val is None:
            return None  # type: ignore[return-value]
        if isinstance(val, cls):
            return val
        if isinstance(val, Text):
            return cls(text=val.text, format=val.format, options=val.options)
        if isinstance(val, str):
            return cls(text=val, format="html")
        raise TypeError(f"Cannot coerce {type(val)} to Feedback")
