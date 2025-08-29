from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias

# Import only for type aliasing; avoid circular imports
from ._text import Feedback, Text, Hint, GraderInfo

# Base building block
TextLike: TypeAlias = Text | str

# Compose upwards so supersets include subsets
FeedbackLike: TypeAlias = Feedback | TextLike
HintLike: TypeAlias = Hint | TextLike
GraderInfoLike: TypeAlias = GraderInfo | TextLike

# Provide precise alias for type checkers, avoid runtime circular import
if TYPE_CHECKING:
    from ._question import QuestionText

    QuestionTextLike: TypeAlias = QuestionText | TextLike
else:
    # At runtime, TextLike is sufficient for annotations
    QuestionTextLike: TypeAlias = TextLike
