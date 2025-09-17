from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Choice:
    key: str
    text: str

    def __post_init__(self) -> None:
        k = self.key.strip()
        t = self.text.strip()
        if not k:
            raise ValueError("Choice.key must be non-empty")
        if not t:
            raise ValueError("Choice.text must be non-empty")
        object.__setattr__(self, "key", k)
        object.__setattr__(self, "text", t)

