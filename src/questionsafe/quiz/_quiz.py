# _quiz.py
from dataclasses import dataclass, field
from typing import (
    Any,
    List,
    Literal,
    Optional,
    Iterator,
    Self,
    Iterable,
    Tuple,
    overload,
)
from pathlib import Path

from ..base._question import Question
from ..questions.category import Category
from ..base._group import QuestionGroup


def _count_questions(items: Iterable) -> Tuple[int, int]:
    n_category = 0
    n_question = 0
    for item in items:
        if isinstance(item, Category):
            n_category += 1
        elif isinstance(item, Question):
            n_question += 1
        else:
            raise ValueError(f"Not an instance of Question: {item}")
    return (n_question, n_category)


@dataclass
class Quiz:
    """A container of category and question objects with optional grouping.

    Attributes
    - questions: List[Question]
        Ordered list of question-like objects (Category or Question) to include.
    - title: Optional[str]
        Optional title used for HTML preview if not provided explicitly.
    - category: Optional[str]
        Parent category path used when adding grouped question variants.
    - subcategory_id: Literal["123", "name"]
        Strategy to name subcategories for groups ("123" or "name").
    """

    questions: List[Question] = field(default_factory=list)
    title: Optional[str] = None
    category: Optional[str] = None
    subcategory_id: Literal["123", "name"] = "123"
    lms: str = "moodle"

    _counter: int = 0
    _total_qn: int = 0

    def __iter__(self) -> Iterator[Question]:
        return iter(self.questions)

    def add(self, *items: Question[Any]) -> Self:
        """Append question-like objects and return self for chaining."""
        nq, _ = _count_questions(items)
        self._total_qn += nq
        self.questions.extend(items)
        return self

    def add_group(
        self,
        questions: Iterable[Question[Any]] | QuestionGroup,
        *,
        idnumber_prefix: Optional[str] = None,
        idnumber_offset: int = 0,
    ) -> Self:
        """Append a group of question variants under a subcategory and assign idnumbers.

        Parameters
        - questions: Iterable[Question] | QuestionGroup
            Variants of a logical question; Category nodes are not allowed.
        - idnumber_prefix: Optional[str]
            Prefix applied to assigned idnumbers (e.g., "v" -> v0, v1, ...).
        - idnumber_offset: int
            Starting index for idnumber assignment within this group.

        Behavior
        - Inserts a Category node for this group. Parent category is self.category
          if set; otherwise, today's date (YYYY-MM-DD) is used.
        - Subcategory name is "Qn" sequence if subcategory_id=="123"; otherwise
          it uses the first question's name when subcategory_id=="name".
        - For each question lacking an idnumber, assign prefix + (offset+i).
        """
        # Normalize to a QuestionGroup
        if isinstance(questions, QuestionGroup):
            group = questions
        else:
            qs_list: List[Question[Any]] = list(questions)
            if not qs_list:
                return self
            group = QuestionGroup(variants=qs_list)

        # Basic validation: no Category nodes inside a QuestionGroup
        nq, nc = _count_questions(group.variants)
        if nc > 0:
            raise TypeError(
                "add_group() does not accept Category nodes; add them via add()."
            )
        self._total_qn += nq

        # Determine parent category
        if not self.category:
            from datetime import date

            parent = date.today().isoformat()
        else:
            parent = self.category

        # Determine subcategory name
        if self.subcategory_id == "name" and len(group.variants) > 0:
            subname = group.variants[0].name
        else:
            self._counter += 1
            subname = f"Q{self._counter}"

        # Insert Category for this group
        self.questions.append(Category(path=f"{parent}/{subname}"))

        # Assign idnumbers and append
        group.assign_idnumbers(prefix=idnumber_prefix, offset=idnumber_offset)
        self.questions.extend(group.variants)
        return self

    def add_category(self, path: str, *, inherit: bool = True) -> Self:
        """Append a Category node, optionally inheriting this quiz's parent category.

        Parameters
        - path: str
            Sub-path or absolute path depending on `inherit`.
        - inherit: bool
            If True (default) and self.category is set, prefix with "{self.category}/".
            If False, use `path` as-is.

        Notes
        - Writer normalization prefixes the first segment with "$course$/" unless the
          first segment is already a token like "$course$".
        - Adding a Category does not affect the question count returned by ``len(quiz)``.
        """
        if inherit and self.category:
            full_path = f"{self.category}/{path}"
        else:
            full_path = path
        # Adding a Category does not affect the question count
        self.add(Category(path=full_path))
        return self

    def __len__(self) -> int:
        return self._total_qn

    def __repr__(self) -> str:
        """Return a compact developer-friendly representation of this Quiz."""
        return (
            f"<Quiz title={self.title!r} category={self.category!r} "
            f"questions={len(self)}>"
        )

    def info(self) -> None:
        """Print a simple textual summary of this quiz.

        Output format
        - First line: total number of non-category questions (i.e., ``len(self)``)
        - Subsequent lines: each item in order
          * Category: ``---- {path} ----``
          * Question: uses the question's ``__str__`` summary
        """
        print(f"Number of questions: {len(self)}\n")

        for q in self.questions:
            if isinstance(q, Category):
                print(f"---- {q.path} ----")
            else:
                print(q)

    def validate(self) -> None:
        """Validate all questions by calling each item's validate() if available.
        Raises ValueError at the first failure encountered.
        """
        for q in self.questions:
            try:
                q.validate()  # type: ignore[attr-defined]
            except AttributeError:
                # e.g., Category
                continue
        return None

    # --- convenience rendering/writing API bound to this Quiz instance ---
    def _resolve_writer(self):
        """Return LMS writer module object based on self.lms.

        Currently supports only "moodle". Raises NotImplementedError for others.
        """
        if self.lms == "moodle":
            from ..writer import (
                moodle as _writer,
            )  # local import to avoid hard dependency for base/questions

            return _writer
        raise NotImplementedError(f"LMS '{self.lms}' is not supported yet")

    @overload
    def to_xml(
        self, file: None = ..., *, templates_dir: str | None = None
    ) -> bytes: ...

    @overload
    def to_xml(self, file: Path | str, *, templates_dir: str | None = None) -> Path: ...

    def to_xml(
        self, file: Path | str | None = None, *, templates_dir: str | None = None
    ) -> bytes | Path:
        """Render or write this quiz to Moodle XML (or other LMS when available).

        - If file is None, returns bytes of XML (uses render_xml).
        - If file is provided, writes to the path and returns Path (uses write_xml).
        """
        w = self._resolve_writer()
        if file is None:
            return w.render_xml(self, templates_dir=templates_dir)
        else:
            return w.write_xml(self, file, templates_dir=templates_dir)

    @overload
    def to_html(
        self,
        file: None = ...,
        *,
        title: str | None = None,
        templates_dir: str | None = None,
    ) -> str: ...

    @overload
    def to_html(
        self,
        file: Path | str,
        *,
        title: str | None = None,
        templates_dir: str | None = None,
    ) -> Path: ...

    def to_html(
        self,
        file: Path | str | None = None,
        *,
        title: str | None = None,
        templates_dir: str | None = None,
    ) -> str | Path:
        """Render or write this quiz to an HTML preview document.

        - If file is None, returns HTML str (uses render_html).
        - If file is provided, writes to the path and returns Path (uses write_html).
        - Title defaults to quiz.title when not provided.
        """
        w = self._resolve_writer()
        if file is None:
            return w.render_html(self, title=title, templates_dir=templates_dir)
        else:
            return w.write_html(self, file, title=title, templates_dir=templates_dir)
