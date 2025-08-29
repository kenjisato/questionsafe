# essay.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List
import copy

from ..base._text import GraderInfo, Text
from ..base._types import GraderInfoLike
from ..base._question import Question


@dataclass
class EssayResponse:
    """User response configuration for Essay questions.

    Maps to Moodle XML fields as follows:
      - format -> <responseformat>
      - input_required -> <responserequired>
      - input_lines -> <responsefieldlines>
      - input_min_words -> <minwordlimit>
      - input_max_words -> <maxwordlimit>
      - attachments_count -> <attachments>
      - attachments_required -> <attachmentsrequired>
      - attachments_maxbytes -> <maxbytes>
      - attachments_filetypelist -> <filetypeslist>
      - template -> <responsetemplate>
    """

    format: Literal["editor", "editorfilepicker", "monospaced", "plain"] = "editor"
    input_required: bool = False
    input_lines: int = 10
    input_min_words: int = 0
    input_max_words: int = 0

    attachments_count: int = 0
    attachments_required: bool = False
    attachments_maxbytes: int = 0
    attachments_filetypelist: List[str] = field(default_factory=list)

    template: Text | str | None = None

    def __post_init__(self) -> None:
        if self.template is not None and not isinstance(self.template, Text):
            self.template = Text(self.template)


@dataclass
class Essay(Question):
    """Essay/free-text response question using a structured response config."""

    response: EssayResponse = field(default_factory=EssayResponse)
    graderinfo: GraderInfo | Text | str | None = None

    qtype: str = "essay"

    def __post_init__(self):  # type: ignore[override]
        # First let base question coerce its own fields
        super().__post_init__()
        # Coerce graderinfo if provided
        if self.graderinfo is not None:
            self.graderinfo = GraderInfo.from_text(self.graderinfo)

    def validate(self) -> None:
        # Validate response settings
        allowed = {"editor", "editorfilepicker", "monospaced", "plain"}
        if self.response.format not in allowed:
            raise ValueError(f"Essay.response.format must be one of {sorted(allowed)}")
        if self.response.input_lines < 0:
            raise ValueError("Essay.response.input_lines must be >= 0")
        if self.response.attachments_count < 0:
            raise ValueError("Essay.response.attachments_count must be >= 0")
        if self.response.input_min_words < 0:
            raise ValueError("Essay.response.input_min_words must be >= 0")
        if self.response.input_max_words < 0:
            raise ValueError("Essay.response.input_max_words must be >= 0")
        if self.response.attachments_maxbytes < 0:
            raise ValueError("Essay.response.attachments_maxbytes must be >= 0")
        # Enforce min < max when both limits are set (non-zero)
        if (
            self.response.input_min_words > 0
            and self.response.input_max_words > 0
            and self.response.input_min_words >= self.response.input_max_words
        ):
            raise ValueError(
                "Essay.response.input_words_min must be < input_words_max when both are set"
            )
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
        self, fmt: Literal["editor", "editorfilepicker", "monospaced", "plain"]
    ) -> "Essay":
        self.response.format = fmt
        return self

    def set_input_required(self, required: bool = True) -> "Essay":
        self.response.input_required = required
        return self

    def set_input_lines(self, lines: int) -> "Essay":
        self.response.input_lines = int(lines)
        return self

    def set_input_words(self, minimum: int | None, maximum: int | None) -> "Essay":
        """Set min/max word limits.

        Usage:
          set_input_words(min, max)
        Use None for open-ended.
        """
        if minimum is not None:
            self.response.input_min_words = int(minimum)
        if maximum is not None:
            self.response.input_max_words = int(maximum)
        return self

    def set_input_words_min(self, minimum: int) -> "Essay":
        self.response.input_min_words = int(minimum)
        return self

    def set_input_words_max(self, maximum: int) -> "Essay":
        self.response.input_max_words = int(maximum)
        return self

    def set_attachments_count(self, count: int) -> "Essay":
        self.response.attachments_count = int(count)
        return self

    def set_attachments_required(self, required: bool = True) -> "Essay":
        self.response.attachments_required = required
        return self

    def set_attachments_maxbytes(self, maxbytes: int) -> "Essay":
        self.response.attachments_maxbytes = int(maxbytes)
        return self

    def set_attachments_filetypes(self, types: List[str]) -> "Essay":
        self.response.attachments_filetypelist = list(types)
        return self

    def set_response_template(self, template: Text | str) -> "Essay":
        self.response.template = (
            template if isinstance(template, Text) else Text(template)
        )
        return self

    def set_graderinfo(self, graderinfo: GraderInfoLike) -> "Essay":
        self.graderinfo = GraderInfo.from_text(graderinfo)
        return self
