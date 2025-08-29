from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterator, List, Optional, Self

from ._question import Question


@dataclass
class QuestionGroup:
    """A set of question variants that belong together.

    Intended to represent the codomain of a template expansion (e.g., QMD/MD -> Questions).

    Attributes
    - variants: List[Question]
        Concrete question instances (no Category nodes).
    - source: Optional[str]
        Optional origin of this group (e.g., path to a QMD/MD file).
    - meta: dict[str, Any]
        Optional metadata for provenance or generation parameters (e.g., seeds).
    """

    variants: List[Question[Any]] = field(default_factory=list)
    source: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Question[Any]]:
        return iter(self.variants)

    def __len__(self) -> int:
        return len(self.variants)

    def add(self, *qs: Question[Any]) -> Self:
        """Append questions to this group and return self."""
        self.variants.extend(qs)
        return self

    def assign_idnumbers(
        self, *, prefix: Optional[str] = None, offset: int = 0
    ) -> Self:
        """Assign idnumbers to any question that lacks one.

        idnumber = f"{prefix}{offset+i}" if prefix else str(offset+i)
        """
        for i, q in enumerate(self.variants):
            if getattr(q, "idnumber", None) in (None, ""):
                val = offset + i
                q.idnumber = f"{prefix}{val}" if prefix else str(val)
        return self
