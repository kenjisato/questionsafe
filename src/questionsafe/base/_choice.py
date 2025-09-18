from __future__ import annotations

from dataclasses import dataclass
from ._text import Text


@dataclass(frozen=True, slots=True)
class Choice:
    key: str
    text: Text | str

    def __post_init__(self) -> None:
        k = self.key.strip()
        if not k:
            raise ValueError("Choice.key must be non-empty")
        object.__setattr__(self, "key", k)
        # Validate non-empty text content; allow Text or str
        if isinstance(self.text, Text):
            content = (self.text.text or "").strip()
            if not content:
                raise ValueError("Choice.text must be non-empty")
            # keep Text instance as-is
        else:
            t = str(self.text).strip()
            if not t:
                raise ValueError("Choice.text must be non-empty")
            object.__setattr__(self, "text", t)

