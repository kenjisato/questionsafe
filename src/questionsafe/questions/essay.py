# essay.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List
import copy
import os

from ..base._text import GraderInfo, Text
from ..base._types import GraderInfoLike
from ..base._question import Question


def _essay_text(val: Text | str | dict) -> Text:
    """Coerce a TextLike, {text, format}, or {path} (file read as HTML)."""
    if isinstance(val, Text):
        return val
    if isinstance(val, dict):
        if "path" not in val:
            return Text(str(val.get("text", "")), format=str(val.get("format", "html")))
        p = os.path.expandvars(os.path.expanduser(str(val.get("path") or "").strip()))
        try:
            return Text(open(p, encoding="utf-8").read() if p and os.path.exists(p) else "")
        except Exception:
            return Text("")
    return Text(str(val))


@dataclass
class EssayTextArea:
    """Textarea configuration for Essay questions.

    - format: editor|editorfilepicker|monospaced|plain|noinline
    - required: whether text input is required
    - lines: number of input lines
    - min_words, max_words: word count constraints (0 disables)
    - template: inline template text (TextLike) or path mapping {path: str}
    """

    format: Literal["editor", "editorfilepicker", "monospaced", "plain", "noinline"] = "editor"
    required: bool = False
    lines: int = 10
    min_words: int = 0
    max_words: int = 0
    template: Text | str | dict | None = None

    def __post_init__(self) -> None:
        if self.template is not None:
            self.template = _essay_text(self.template)


@dataclass
class EssayAttachments:
    count: int = 0
    required: bool = False
    maxbytes: int = 0
    filetypelist: List[str] = field(default_factory=list)


@dataclass
class EssayResponse:
    """User response configuration for Essay questions using grouped fields."""

    textarea: EssayTextArea = field(default_factory=EssayTextArea)
    attachments: EssayAttachments = field(default_factory=EssayAttachments)


@dataclass
class Essay(Question):
    """Essay/free-text response question using a structured response config."""

    response: EssayResponse = field(default_factory=EssayResponse)
    graderinfo: GraderInfo | Text | str | dict | None = None

    qtype: str = "essay"

    def __post_init__(self):  # type: ignore[override]
        # First let base question coerce its own fields
        super().__post_init__()
        if self.graderinfo is not None:
            self.graderinfo = GraderInfo.from_text(_essay_text(self.graderinfo))

    def validate(self) -> None:
        # Validate response settings
        allowed = {"editor", "editorfilepicker", "monospaced", "plain"}
        ta = self.response.textarea
        at = self.response.attachments
        allowed = {"editor", "editorfilepicker", "monospaced", "plain", "noinline"}
        if ta.format not in allowed:
            raise ValueError(f"Essay.response.textarea.format must be one of {sorted(allowed)}")
        if ta.lines < 0:
            raise ValueError("Essay.response.textarea.lines must be >= 0")
        if at.count < 0:
            raise ValueError("Essay.response.attachments.count must be >= 0")
        if ta.min_words < 0:
            raise ValueError("Essay.response.textarea.min_words must be >= 0")
        if ta.max_words < 0:
            raise ValueError("Essay.response.textarea.max_words must be >= 0")
        if at.maxbytes < 0:
            raise ValueError("Essay.response.attachments.maxbytes must be >= 0")
        # Enforce min < max when both limits are set (non-zero)
        if ta.min_words > 0 and ta.max_words > 0 and ta.min_words >= ta.max_words:
            raise ValueError("Essay.response.textarea.min_words must be < max_words when both are set")
        # Special rule: noinline requires at least one required attachment
        if ta.format == "noinline":
            if at.count <= 0 or not at.required:
                raise ValueError("textarea.format='noinline' requires attachments.count>0 and attachments.required=true")
        return None

    # ----- Fluent setters (set_-prefixed) -----
    def set_response(self, response: EssayResponse) -> "Essay":
        """Replace the entire response configuration in one call.

        The provided response is deep-copied to avoid shared mutable state
        between questions.
        """
        self.response = copy.deepcopy(response)
        return self

    def set_response_format(
        self, fmt: Literal["editor", "editorfilepicker", "monospaced", "plain", "noinline"]
    ) -> "Essay":
        self.response.textarea.format = fmt
        return self

    def set_input_required(self, required: bool = True) -> "Essay":
        self.response.textarea.required = required
        return self

    def set_input_lines(self, lines: int) -> "Essay":
        self.response.textarea.lines = int(lines)
        return self

    def set_input_words(self, minimum: int | None, maximum: int | None) -> "Essay":
        """Set min/max word limits.

        Usage:
          set_input_words(min, max)
        Use None for open-ended.
        """
        if minimum is not None:
            self.response.textarea.min_words = int(minimum)
        if maximum is not None:
            self.response.textarea.max_words = int(maximum)
        return self

    def set_input_words_min(self, minimum: int) -> "Essay":
        self.response.textarea.min_words = int(minimum)
        return self

    def set_input_words_max(self, maximum: int) -> "Essay":
        self.response.textarea.max_words = int(maximum)
        return self

    def set_attachments_count(self, count: int) -> "Essay":
        self.response.attachments.count = int(count)
        return self

    def set_attachments_required(self, required: bool = True) -> "Essay":
        self.response.attachments.required = required
        return self

    def set_attachments_maxbytes(self, maxbytes: int) -> "Essay":
        self.response.attachments.maxbytes = int(maxbytes)
        return self

    def set_attachments_filetypes(self, types: List[str]) -> "Essay":
        self.response.attachments.filetypelist = list(types)
        return self

    def set_response_template(self, template: Text | str | dict) -> "Essay":
        # Accept TextLike, {text, format}, or {path}
        self.response.textarea.template = _essay_text(template)
        return self

    def set_graderinfo(self, graderinfo: GraderInfoLike | dict | str) -> "Essay":
        # Accept TextLike, {text, format}, or {path}; a str naming a file is read
        if isinstance(graderinfo, str):
            s = os.path.expandvars(os.path.expanduser(graderinfo))
            if os.path.isfile(s):
                graderinfo = {"path": s}
        self.graderinfo = GraderInfo.from_text(_essay_text(graderinfo))
        return self
