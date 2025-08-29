# cloze.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, Literal

from ..base import Question
from ._cloze_embed import ClozeEmbeddable

@dataclass
class Cloze(Question):
    """Embedded (CLOZE) question composed inline in the question text.

    Placeholders in the stem use double square brackets: ``[[identifier]]``.
    Register embedded questions with ``embed_question()`` where the embedded
    question's ``name`` provides the ``identifier``.
    """

    qtype: str = "cloze"
    # name -> (question, orientation, weight)
    _embedded: Dict[str, tuple[ClozeEmbeddable, Optional[Literal["v", "h"]], int]] = field(
        default_factory=dict
    )

    def embed_question(
        self, q: ClozeEmbeddable, *, orientation: Optional[Literal["v", "h"]] = None, weight: int = 1
    ) -> "Cloze":
        """Embed a sub-question referenced by its identifier in questiontext.

        Parameters
        - q: SingleChoice | MultiChoice | ShortAnswer | Numerical
            Embedded sub-question. Its ``name`` is used as the placeholder
            identifier and must exist in the stem as ``[[name]]``.
        - orientation: Optional[Literal["v", "h"]]
            Orientation for choice-based questions (ignored for ShortAnswer and Numerical):
            - SingleChoice: None -> MC (dropdown), "v" -> MCV (vertical radios), "h" -> MCH (horizontal radios)
            - MultiChoice:  None or "v" -> MR (vertical checkboxes), "h" -> MRH (horizontal checkboxes)
        - weight: int
            Cloze item weighting (nonnegative integer). Defaults to 1.
        """
        name = getattr(q, "name", None)
        if not name:
            raise ValueError("Embedded question must have a non-empty name as identifier")
        if not isinstance(q, ClozeEmbeddable):
            raise TypeError("Embedded question must implement ClozeEmbeddable")
        # Validate weight centrally
        w = q._validate_weight(weight)
        if name in self._embedded:
            raise ValueError(f"Duplicate embedded identifier: {name!r}")
        self._embedded[name] = (q, orientation, w)
        return self

    # Public helper for writer and users: produce inline CLOZE tokens and replace placeholders
    def compile_text(self) -> str:
        text = self.questiontext.text  # type: ignore[attr-defined]
        for ident, (subq, orientation, weight) in self._embedded.items():
            token = subq.cloze(orientation=orientation, weight=weight)
            placeholder = f"[[{ident}]]"
            text = text.replace(placeholder, token)
        return text
