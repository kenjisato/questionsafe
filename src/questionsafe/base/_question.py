# _question.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Generic, TypeVar, Self

from ._text import Text, Feedback
from ._answer import _AnswerBase

# Type parameter for the Answer kind a Question works with
A = TypeVar("A", bound=_AnswerBase)


@dataclass
class QuestionText(Text):
    """
    <questiontext> ... </questiontext>
    """

    @classmethod
    def from_text(cls, val: Self | Text | str) -> Self:
        if isinstance(val, cls):
            return val
        if isinstance(val, Text):
            return cls(text=val.text, format=val.format, options=val.options)
        if isinstance(val, str):
            return cls(text=val, format="html")
        raise TypeError(f"Cannot coerce {type(val)} to QuestionText")


@dataclass
class Question(Generic[A]):
    """Base class for all question types.

    Attributes
    - name: str
        Question name as shown in the question bank.
    - questiontext: QuestionText
        The question stem/content.
    - feedback_general: Optional[Feedback]
        Feedback shown after the question is attempted.
    - defaultgrade: float
        Default point value (default 1.0).
    - tags: List[str]
        Optional tags for organizing questions.
    - idnumber: str
        Optional idnumber for making a variant distinguishable from another.
    - qtype: str
        Internal Moodle qtype string; set by subclasses.
    """

    name: str = ""
    # Accept flexible input type (coerced in __post_init__), but keep strong runtime type
    # Provide a default to allow lazy initialization via set_question()/ask()
    questiontext: QuestionText | Text | str = ""
    feedback_general: Feedback | Text | str | None = None
    defaultgrade: float = 1.0
    tags: List[str] = field(default_factory=list)
    idnumber: Optional[str] = None

    # override in subclasses
    qtype: str = "base"

    def __post_init__(self):
        # Coerce provided questiontext into a proper QuestionText instance
        self.questiontext = QuestionText.from_text(self.questiontext)
        # Coerce general feedback if provided
        if self.feedback_general is not None:
            self.feedback_general = Feedback.from_text(self.feedback_general)

    def validate(self) -> None:
        """Base validation hook. Subclasses/mixins may extend.

        Ensures that name and questiontext are non-empty, which is required by Moodle.
        """
        # Validate name
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must not be empty")
        # Some special nodes (e.g., Category) may override this check for questiontext.
        try:
            text = (self.questiontext.text or "").strip()  # type: ignore[attr-defined]
        except Exception:
            text = ""
        if text == "":
            raise ValueError("questiontext must not be empty")
        return None

    # -------- Fluent setters for common question attributes --------
    def set_name(self, name: str):
        """Set the question bank name; returns self for fluent chaining."""
        self.name = name
        return self

    def set_questiontext(self, questiontext: QuestionText | Text | str):
        """Set the question stem using the standardized Text coercion."""
        self.questiontext = QuestionText.from_text(questiontext)
        return self

    # Aliases for ergonomics
    def set_question(self, question: QuestionText | Text | str):
        """Alias of set_questiontext for brevity."""
        return self.set_questiontext(question)

    def ask(self, question: QuestionText | Text | str):
        """Very fluent alias of set_questiontext."""
        return self.set_questiontext(question)

    def set_feedback_general(self, feedback: Feedback | Text | str | None):
        """Set general feedback using standardized Text coercion."""
        self.feedback_general = Feedback.from_text(feedback)
        return self

    def set_defaultgrade(self, grade: float):
        """Set the default grade (points), typically 1.0."""
        self.defaultgrade = float(grade)
        return self

    def set_tags(self, *tags: str):
        """Replace the list of tags."""
        self.tags = list(tags)
        return self

    def add_tag(self, tag: str):
        """Append a single tag."""
        self.tags.append(tag)
        return self

    def set_idnumber(self, idnumber: Optional[str]):
        """Set or clear the idnumber used for cross-referencing/questions bank IDs."""
        self.idnumber = idnumber
        return self

    # Low-level API hook: subclasses that support answers should override this.
    def add_answer(self, _answer: A):  # pragma: no cover - overridden in subclasses
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support add_answer(); use the high-level API instead."
        )

    # Low-level API hook: subclasses that support answers should override this.
    def set_answers(self, *_answers: A):  # pragma: no cover - overridden in subclasses
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support set_answers(); use the high-level API instead."
        )

    def __str__(self) -> str:
        """Return a concise, human-friendly representation of the question.

        Combines the class name, question bank name, and the first 40 characters of
        the stem text. Intended for logs, diagnostics, and summary listings (e.g.,
        Quiz.info()).
        """
        text = self.questiontext.text  # type: ignore
        return f"{self.__class__.__name__}('{self.name}', '{text[:40]}...', ...)"

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation for REPL/debugging."""
        return (
            f"<{self.__class__.__name__} name={self.name!r} qtype={self.qtype!r} "
            f"idnumber={self.idnumber!r}>"
        )

    # ---- Semantic equality (delegating to components) ----
    @staticmethod
    def _round(v: float | int | None, nd: int = 7) -> float | None:
        if v is None:
            return None
        try:
            return round(float(v), nd)
        except Exception:
            return float(v) if v is not None else None

    @staticmethod
    def _key_textlike(v: Feedback | Text | QuestionText | str | None):
        if v is None:
            return None
        if hasattr(v, "_eq_key") and callable(v._eq_key):
            return (type(v).__name__, v._eq_key())
        if isinstance(v, str):
            return ("Text", (v, "html", {}))
        # Fallback to tuple of known fields
        return (type(v).__name__, getattr(v, "text", None), getattr(v, "format", None))

    @staticmethod
    def _key_answers(ans_list):
        if not isinstance(ans_list, list):
            return None
        keys = []
        for a in ans_list:
            if hasattr(a, "_eq_key") and callable(a._eq_key):
                keys.append((type(a).__name__, a._eq_key()))
            else:
                # Text vs Numerical fallbacks
                if hasattr(a, "text"):
                    keys.append((
                        "TextAnswer",
                        str(getattr(a, "text", "")),
                        Question._round(getattr(a, "fraction", 0.0)),
                        str(getattr(a, "format", "")),
                    ))
                elif hasattr(a, "value"):
                    keys.append((
                        "NumericalAnswer",
                        Question._round(getattr(a, "value", None), 9),
                        Question._round(getattr(a, "tolerance", None), 9),
                        Question._round(getattr(a, "fraction", 0.0)),
                        str(getattr(a, "format", "")),
                    ))
                else:
                    keys.append(("Other", repr(a)))
        try:
            keys.sort()
        except Exception:
            pass
        return keys

    def _eq_key(self):
        base = {
            "qtype": str(getattr(self, "qtype", "")),
            "name": str(getattr(self, "name", "")),
            "questiontext": self._key_textlike(getattr(self, "questiontext", None)),
            "feedback_general": self._key_textlike(getattr(self, "feedback_general", None)),
            "defaultgrade": self._round(getattr(self, "defaultgrade", 1.0)),
            "tags": tuple(sorted([str(t) for t in list(getattr(self, "tags", []) or [])])),
            "idnumber": getattr(self, "idnumber", None),
        }
        # Choice-like flags
        for attr in ("single", "shuffleanswers", "answernumbering", "usecase"):
            if hasattr(self, attr):
                base[attr] = getattr(self, attr)
        # Units (dataclass equality)
        if hasattr(self, "units"):
            base["units"] = self.units
        # Answers (order-insensitive)
        base["answers"] = self._key_answers(getattr(self, "answers", None))
        # MultiTry (only when enabled)
        if hasattr(self, "has_hints") and bool(self.has_hints):
            hints = []
            for h in list(getattr(self, "hints", []) or []):
                hints.append(self._key_textlike(h))
            base["hints"] = tuple(hints)
            base["penalty"] = self._round(getattr(self, "penalty", None))
        # Combined feedback (only when enabled)
        if hasattr(self, "has_combined_feedback") and bool(self.has_combined_feedback):
            base["feedback_combined"] = (
                self._key_textlike(getattr(self, "feedback_correct", None)),
                self._key_textlike(getattr(self, "feedback_partiallycorrect", None)),
                self._key_textlike(getattr(self, "feedback_incorrect", None)),
            )
        return base

    def __eq__(self, other: object) -> bool:  # type: ignore[override]
        if not isinstance(other, Question):
            return NotImplemented
        return self._eq_key() == other._eq_key()
