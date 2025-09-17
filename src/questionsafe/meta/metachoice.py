# MetaChoice scaffolding
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Mapping, Any, Union

from ..base._choice_sampling import Constraint as BaseConstraint, constrained_subsets
from ..questions.multichoice import MultiChoice
from ..questions.singlechoice import SingleChoice
from ..base._answer import Answer, TextAnswer
from ..base._constraints import ALLOWED_FRACTIONS_POS
from ..base._group import QuestionGroup


def _allowed_uniform_counts() -> Set[int]:
    # Allowed counts n such that 100/n is exactly one of ALLOWED_FRACTIONS_POS
    out: Set[int] = set()
    for f in ALLOWED_FRACTIONS_POS:
        if f <= 0:
            continue
        n = round(100.0 / f)
        if abs(100.0 / n - f) <= 1e-6:
            out.add(int(n))
    return out


ALLOWED_UNIFORM_COUNTS = _allowed_uniform_counts()


def _coerce_text(val: TextAnswer | str) -> str:
    """Coerce TextAnswer|str to normalized non-empty text (HTML assumed)."""
    if isinstance(val, str):
        t = val.strip()
    else:
        t = Answer.from_text(val).text.strip()
    if not t:
        raise ValueError("Choice text cannot be empty")
    return t


@dataclass
class Choice:
    key: str
    text: str


@dataclass(frozen=True)
class Constraint:
    id: str
    members: frozenset[str]
    min: int = 0
    max: Optional[int] = None
    description: Optional[str] = None

    def __init__(
        self,
        id: str,
        *,
        choices: Iterable[Union[str, Choice]],
        min: int = 0,
        max: Optional[int] = None,
        description: Optional[str] = None,
    ) -> None:
        ks: Set[str] = set()
        for c in choices:
            if isinstance(c, Choice):
                k = c.key.strip()
            else:
                k = str(c).strip()
            if not k:
                raise ValueError("Constraint choices must have non-empty keys")
            ks.add(k)
        object.__setattr__(self, "id", str(id))
        object.__setattr__(self, "members", frozenset(ks))
        object.__setattr__(self, "min", int(min))
        object.__setattr__(self, "max", None if max is None else int(max))
        object.__setattr__(self, "description", description)

    def to_base_constraint(self) -> BaseConstraint:
        return BaseConstraint(id=self.id, members=self.members, min=self.min, max=self.max, description=self.description)


def _coerce_to_choice_list(obj: Any) -> List[Choice]:
    """Coerce various forms into a list of Choice(key, text).

    Accepted forms
    - Choice -> [Choice]
    - Mapping[str, str] -> [Choice(k, v), ...]
    - str -> if "key: text" use the first colon to split; else key==text
    - Iterable of the above -> flattened list
    """
    # Single item cases
    if isinstance(obj, Choice):
        k = obj.key.strip()
        if not k:
            raise ValueError("Choice key must be a non-empty string")
        if not obj.text.strip():
            raise ValueError("Choice text cannot be empty")
        return [obj]
    if isinstance(obj, Mapping):
        out: List[Choice] = []
        for k_in, t_in in obj.items():
            k = str(k_in).strip()
            t = str(t_in)
            if not k:
                raise ValueError("Choice key must be a non-empty string")
            if not t.strip():
                raise ValueError("Choice text cannot be empty")
            out.append(Choice(k, t))
        return out
    if isinstance(obj, str):
        raw = obj.strip()
        if ":" in raw:
            left, _, right = raw.partition(":")
            k = left.strip()
            t = right.lstrip()
        else:
            k = raw
            t = raw
        if not k:
            raise ValueError("Choice key must be a non-empty string")
        if not t.strip():
            raise ValueError("Choice text cannot be empty")
        return [Choice(k, t)]

    # Iterable case (but avoid treating string/mapping as iterable here)
    try:
        it = iter(obj)  # type: ignore
    except TypeError:
        raise TypeError("Unsupported choice input type")
    out: List[Choice] = []
    for item in it:  # type: ignore
        out.extend(_coerce_to_choice_list(item))
    return out


@dataclass
class Stem:
    key: str
    text: str
    local_groups: Sequence[BaseConstraint] = field(default_factory=tuple)

    def set_choices_correct(self, items: Iterable[Union[str, Choice]]) -> "Stem":
        ms: Set[str] = set()
        for it in items:
            if isinstance(it, Choice):
                k = it.key.strip()
            else:
                k = str(it).strip()
            if k:
                ms.add(k)
        correct = BaseConstraint(id="__correct__", members=ms, min=1, max=None, description=None)
        lgs = [g for g in self.local_groups if g.id != "__correct__"]
        lgs.append(correct)
        self.local_groups = tuple(lgs)
        return self

    def add_constraint(self, constraint: Constraint) -> "Stem":
        if constraint.id == "__correct__":
            raise ValueError("'__correct__' is reserved; use set_choices_correct() instead")
        gs = constraint.to_base_constraint()
        lgs = list(self.local_groups)
        lgs.append(gs)
        self.local_groups = tuple(lgs)
        return self


@dataclass
class MetaChoice:
    """Build MultiChoice questions from a shared pool with global + per-stem constraints.

    High-level idea
    - Maintain a pool of candidate choices (strings) shared across stems.
    - Define constraint groups globally (apply to all stems) and locally per-stem.
    - For each stem, sample up to `limit` subsets of size `n` satisfying all constraints.
      Correct choices are designated by a reserved local group added via Stem.set_group_correct.

    Usage
    - Define a global pool of choices via set_choices/add_choices/add_choice.
    - Register global constraint groups via add_group (applies to all stems).
    - Create stems as data objects and register them via add_stem.
    - Generate MultiChoice questions with generate_multichoice().
    """

    _choices: Dict[str, Choice] = field(default_factory=dict)  # key -> Choice
    _global_groups: Dict[str, BaseConstraint] = field(default_factory=dict)
    _stems: List[Stem] = field(default_factory=list)

    # Choice pool management (keys + text)
    def set_choices(self, choices: Any) -> "MetaChoice":
        """Replace the entire choice pool.

        Preferred input is an iterable of Choice; shorthand inputs are coerced:
        - Mapping[str, str] becomes Choices by items.
        - str or iterable of str can use "key: text"; if no colon, key==text.
        """
        items = _coerce_to_choice_list(choices)
        new_map: Dict[str, Choice] = {}
        for ch in items:
            k = ch.key.strip()
            if k in new_map:
                raise ValueError(f"Duplicate choice key: {k}")
            new_map[k] = ch
        self._choices = new_map
        return self

    def _add_choice_internal(self, ch: Choice) -> None:
        k = ch.key.strip()
        if not k:
            raise ValueError("Choice key must be a non-empty string")
        if not ch.text.strip():
            raise ValueError("Choice text cannot be empty")
        if k in self._choices:
            raise ValueError(f"Duplicate choice key: {k}")
        self._choices[k] = ch

    def add_choices(self, *choices: Any) -> "MetaChoice":
        """Append multiple choices to the pool (deduped by key).

        Preferred input is Choice objects; shorthand inputs are coerced.
        """
        for obj in choices:
            for ch in _coerce_to_choice_list(obj):
                self._add_choice_internal(ch)
        return self

    def add_choice(self, choice: Any) -> "MetaChoice":
        """Append one choice (or shorthand) to the pool (by key)."""
        items = _coerce_to_choice_list(choice)
        if not items:
            return self
        self._add_choice_internal(items[0])
        return self

    # Global constraints
    def add_constraint(self, constraint: Constraint) -> "MetaChoice":
        if constraint.id == "__correct__":
            raise ValueError("'__correct__' is reserved; use Stem.set_choices_correct() instead")
        ks = set(constraint.members)
        pool_set = set(self._choices.keys())
        if not ks.issubset(pool_set):
            missing = sorted(ks - pool_set)
            raise ValueError(f"Global constraint '{constraint.id}' has members not in pool: {missing}")
        self._global_groups[constraint.id] = constraint.to_base_constraint()
        return self

    # Stem creation
    def add_stem(self, stem: Stem) -> Stem:
        """Register a stem. Returns the same stem for fluent chaining."""
        if not isinstance(stem, Stem):
            raise TypeError("add_stem expects a Stem instance")
        k = str(stem.key).strip()
        if not k:
            raise ValueError("Stem.key must be a non-empty string")
        self._stems.append(stem)
        return stem

    def _constraints_for_stem(self, stem: Stem) -> List[BaseConstraint]:
        # Conjoin global + local by passing both; same-id groups are not merged but both enforced.
        groups: List[BaseConstraint] = list(self._global_groups.values()) + list(stem.local_groups)
        # Validate that all group members are known keys
        pool_set = set(self._choices.keys())
        for g in groups:
            diff = set(g.members) - pool_set
            if diff:
                raise ValueError(f"Group {g.id} has members not in pool: {sorted(diff)}")
        return groups

    def _pick_subsets(
        self,
        *,
        pool: Sequence[str],
        groups: Sequence[BaseConstraint],
        n: int,
        seed: Optional[int],
        limit: int,
        randomize_order: bool,
        randomize_branch: bool,
    ) -> List[List[str]]:
        it = constrained_subsets(
            pool,
            groups,
            n,
            limit=limit,
            seed=seed,
            randomize_order=randomize_order,
            randomize_branch=randomize_branch,
        )
        pos = {p: i for i, p in enumerate(pool)}
        out: List[List[str]] = []
        for s in it:
            out.append(sorted(s, key=lambda x: pos[x]))
        if not out:
            raise ValueError("No feasible subset satisfying constraints; adjust group bounds or n")
        return out

    def generate_multichoice(
        self,
        *,
        n: int,
        limit: int = 1,
        seed: Optional[int] = None,
        randomize_order: bool = True,
        randomize_branch: bool = True,
        nc: Optional[int | tuple[int, int]] = None,
    ) -> QuestionGroup:
        """Generate MultiChoice questions for each stem and return a QuestionGroup.

        Parameters
        - n: number of choices to sample per generated MCQ (uniform across stems).
        - limit: max number of distinct combinations per stem (>=1). Each combination
                 yields one MultiChoice question.
        - seed: optional base seed; per-stem seeds are derived deterministically from it.
        - randomize_order: whether to randomize the order of items before search.
        - randomize_branch: whether to randomize include/skip decisions during search.
        - nc: constrain the number of correct choices per sampled subset.
              If an int, exactly that many corrects.
              If a (min,max) tuple, range of allowed corrects, inclusive.
              If None, use the bounds from the defined "__correct__" group.

        Parameters
        - n: number of choices to sample per generated MCQ (uniform across stems).
        - limit: max number of distinct combinations per stem (>=1). Each combination
                 yields one MultiChoice question.
        - seed: optional base seed; per-stem seeds are derived deterministically from it.
        - randomize_order: whether to randomize the order of items before search.
        - randomize_branch: whether to randomize include/skip decisions during search.
        """
        if not self._choices:
            raise ValueError("Choice pool is empty; call set_choices()/add_choice() first")
        if limit <= 0:
            raise ValueError("limit must be >= 1")
        out: List[MultiChoice] = []
        base_seed = int(seed) if seed is not None else None
        for idx, stem in enumerate(self._stems):
            raw_groups = self._constraints_for_stem(stem)
            # Optionally adjust correct-group bounds per nc
            if nc is None:
                groups = raw_groups
            else:
                # normalize nc
                if isinstance(nc, int):
                    kmin = kmax = int(nc)
                else:
                    a, b = nc
                    kmin, kmax = int(min(a, b)), int(max(a, b))
                if kmin < 0 or kmax < 0 or kmin > kmax or kmax > n:
                    raise ValueError("Invalid nc bounds; must satisfy 0 <= min <= max <= n")
                groups = []
                saw_correct = False
                for g in raw_groups:
                    if g.id == "__correct__":
                        saw_correct = True
                        groups.append(
                            BaseConstraint(id=g.id, members=g.members, min=kmin, max=kmax, description=g.description)
                        )
                    else:
                        groups.append(g)
                if not saw_correct:
                    raise ValueError("No correct group defined for stem; call set_choices_correct")
            # derive per-stem seed deterministically
            stem_seed = None if base_seed is None else (base_seed + idx)
            subsets = self._pick_subsets(
                pool=list(self._choices.keys()),
                groups=groups,
                n=int(n),
                seed=stem_seed,
                limit=int(limit),
                randomize_order=bool(randomize_order),
                randomize_branch=bool(randomize_branch),
            )
            for subset in subsets:
                # Determine correct items from reserved local group
                correct_members: Set[str] = set()
                for g in stem.local_groups:
                    if g.id == "__correct__":
                        correct_members.update(g.members)

                correct_in_subset = [k for k in subset if k in correct_members]
                wrong_in_subset = [k for k in subset if k not in correct_members]

                # Enforce at least one correct; compute uniform fractions for corrects
                k = len(correct_in_subset)
                if k <= 0:
                    raise RuntimeError("Invariant violated: subset must include at least one correct")

                per = 100.0 / k

                # Name questions using the required stem key
                q = MultiChoice(name=stem.key)
                q.set_questiontext(stem.text)
                for ck in correct_in_subset:
                    q.add_answer(Answer.from_text(self._choices[ck].text, fraction=per))
                for wk in wrong_in_subset:
                    q.add_answer(Answer.from_text(self._choices[wk].text, fraction=0.0))
                q.validate()
                out.append(q)
        return QuestionGroup(variants=out)

    def generate_singlechoice(
        self,
        *,
        n: int,
        limit: int = 1,
        seed: Optional[int] = None,
        randomize_order: bool = True,
        randomize_branch: bool = True,
    ) -> QuestionGroup:
        """Generate SingleChoice questions for each stem and return a QuestionGroup.

        Behavior
        - Internally tightens the reserved "__correct__" group bounds to exactly one
          (min=1, max=1) for sampling. If a stem config has min>1, raises ValueError.
        """
        if not self._choices:
            raise ValueError("Choice pool is empty; call set_choices()/add_choice() first")
        if limit <= 0:
            raise ValueError("limit must be >= 1")
        out: List[SingleChoice] = []
        base_seed = int(seed) if seed is not None else None
        for idx, stem in enumerate(self._stems):
            raw_groups = self._constraints_for_stem(stem)
            adjusted: List[BaseConstraint] = []
            saw_correct = False
            for g in raw_groups:
                if g.id == "__correct__":
                    saw_correct = True
                    if g.min > 1:
                        raise ValueError("generate_singlechoice requires correct-group min<=1")
                    adjusted.append(BaseConstraint(id=g.id, members=g.members, min=1, max=1, description=g.description))
                else:
                    adjusted.append(g)
            if not saw_correct:
                raise ValueError("No correct group defined for stem; call set_choices_correct")

            stem_seed = None if base_seed is None else (base_seed + idx)
            subsets = self._pick_subsets(
                pool=list(self._choices.keys()),
                groups=adjusted,
                n=int(n),
                seed=stem_seed,
                limit=int(limit),
                randomize_order=bool(randomize_order),
                randomize_branch=bool(randomize_branch),
            )
            for subset in subsets:
                # After adjustment, there must be exactly one correct key in the subset
                correct_members: Set[str] = set()
                for g in adjusted:
                    if g.id == "__correct__":
                        correct_members.update(g.members)
                correct_in_subset = [k for k in subset if k in correct_members]
                if len(correct_in_subset) != 1:
                    raise RuntimeError("Internal error: expected exactly one correct after constraint adjustment")
                chosen = correct_in_subset[0]

                q = SingleChoice(name=stem.key)
                q.set_questiontext(stem.text)
                q.add_answer(Answer.from_text(self._choices[chosen].text, fraction=100.0))
                for wk in (k for k in subset if k != chosen):
                    q.add_answer(Answer.from_text(self._choices[wk].text, fraction=0.0))
                q.validate()
                out.append(q)
        return QuestionGroup(variants=out)

