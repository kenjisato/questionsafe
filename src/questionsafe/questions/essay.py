# essay.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List
import copy

from ..base._text import GraderInfo, Text
from ..base._types import GraderInfoLike
from ..base._question import Question


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
        # Coerce template: TextLike or {path: str}
        tpl = self.template
        if tpl is None:
            return
        from os import path as _p
        import os as _os
        if isinstance(tpl, dict) and "path" in tpl:
            p = str(tpl.get("path") or "").strip()
            p = _os.path.expandvars(_os.path.expanduser(p))
            if p:
                try:
                    text = _p.exists(p) and open(p, "r", encoding="utf-8").read() or ""
                except Exception:
                    text = ""
                self.template = Text(text)
            else:
                self.template = None
        elif isinstance(tpl, Text):
            # leave as-is
            pass
        elif isinstance(tpl, str):
            # treat as inline text (not path) to avoid surprising reads
            self.template = Text(tpl)
        else:
            self.template = Text(str(tpl))


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
        # Coerce graderinfo if provided (TextLike or {path})
        if self.graderinfo is not None:
            gi = self.graderinfo
            from os import path as _p
            import os as _os
            if isinstance(gi, dict) and "path" in gi:
                p = str(gi.get("path") or "").strip()
                p = _os.path.expandvars(_os.path.expanduser(p))
                data = ""
                if p:
                    try:
                        data = _p.exists(p) and open(p, "r", encoding="utf-8").read() or ""
                    except Exception:
                        data = ""
                self.graderinfo = GraderInfo.from_text(Text(data))
            else:
                self.graderinfo = GraderInfo.from_text(gi)

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
        # Accept TextLike or {path}
        if isinstance(template, dict) and "path" in template:
            from os import path as _p
            import os as _os
            p = str(template.get("path") or "").strip()
            p = _os.path.expandvars(_os.path.expanduser(p))
            data = ""
            if p:
                try:
                    data = _p.exists(p) and open(p, "r", encoding="utf-8").read() or ""
                except Exception:
                    data = ""
            self.response.textarea.template = Text(data)
        else:
            self.response.textarea.template = (
                template if isinstance(template, Text) else Text(template)
            )
        return self

    def set_graderinfo(self, graderinfo: GraderInfoLike | dict | str) -> "Essay":
        # Accept Text/GraderInfo/str or {path}
        if isinstance(graderinfo, dict) and "path" in graderinfo:
            from os import path as _p
            import os as _os
            p = str(graderinfo.get("path") or "").strip()
            p = _os.path.expandvars(_os.path.expanduser(p))
            data = ""
            if p:
                try:
                    data = _p.exists(p) and open(p, "r", encoding="utf-8").read() or ""
                except Exception:
                    data = ""
            self.graderinfo = GraderInfo.from_text(Text(data))
        elif isinstance(graderinfo, str):
            # Expand env vars; if path exists, read file, else treat as literal
            import os as _os
            from os import path as _p
            s = _os.path.expandvars(_os.path.expanduser(graderinfo))
            if _p.exists(s) and _p.isfile(s):
                try:
                    data = open(s, "r", encoding="utf-8").read()
                except Exception:
                    data = graderinfo
                self.graderinfo = GraderInfo.from_text(Text(data))
            else:
                self.graderinfo = GraderInfo.from_text(graderinfo)
        else:
            self.graderinfo = GraderInfo.from_text(graderinfo)
        return self
