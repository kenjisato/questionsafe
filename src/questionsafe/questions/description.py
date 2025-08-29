# description.py
from __future__ import annotations
from dataclasses import dataclass

from ..base import Question


@dataclass
class Description(Question):
    """Non-graded description block.

    Attributes
    - qtype: str
        Internal type identifier 'description'.
    """

    qtype: str = "description"

    def validate(self) -> None:
        # No special validation rules for description questions
        return None
