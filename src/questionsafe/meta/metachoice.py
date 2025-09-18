# MetaChoice scaffolding
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Mapping, Any, Union
from copy import deepcopy

from ..base._choice_sampling import Constraint as BaseConstraint, constrained_subsets
from ..base._choice import Choice
from ..base._text import Text
from ..questions.multichoice import MultiChoice
from ..questions.singlechoice import SingleChoice
from ..base._answer import Answer
from ..base._group import QuestionGroup


CORRECT_GROUP_ID = "__correct__"

class Constraint(BaseConstraint):
    def __init__(
        self,
        *members: str,
        min: int = 0,
        max: Optional[int] = None,
        id: Optional[str] = None,
    ) -> None:
        """Strict constructor: members as positional keys; optional id for debug.

        Example: Constraint("T1", "T2", min=1, max=1, id="term")
        """
        ks: Set[str] = set()
        for m in members:
            k = str(m).strip()
            if not k:
                raise ValueError("Constraint members must be non-empty strings")
            ks.add(k)
        super().__init__(id=str(id or ""), members=frozenset(ks), min=int(min), max=None if max is None else int(max), description=None)


# No coercion helpers in strict API; set_choices accepts only a Mapping[str, Text|str]


@dataclass(slots=True)
class Stem:
    key: str
    text: str
    local_groups: Sequence[BaseConstraint] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not str(self.key).strip():
            raise ValueError("Stem.key must be a non-empty string")
        if not str(self.text).strip():
            raise ValueError("Stem.text must be a non-empty string")

    def set_choices_correct(self, items: Iterable[Union[str, Choice]]) -> "Stem":
        ms: Set[str] = {
            (it.key.strip() if isinstance(it, Choice) else str(it).strip())
            for it in items
            if (isinstance(it, Choice) and it.key.strip()) or (not isinstance(it, Choice) and str(it).strip())
        }
        correct = BaseConstraint(id=CORRECT_GROUP_ID, members=ms, min=1, max=None, description=None)
        self.local_groups = tuple(g for g in self.local_groups if g.id != CORRECT_GROUP_ID) + (correct,)
        return self

    def add_constraint(self, constraint: BaseConstraint) -> "Stem":
        if constraint.id == CORRECT_GROUP_ID:
            raise ValueError("'__correct__' is reserved; use set_choices_correct() instead")
        self.local_groups = tuple(self.local_groups) + (constraint,)
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
    def set_choices(self, choices: Mapping[str, Union[Text, str]]) -> "MetaChoice":
        """Replace the entire choice pool using a mapping key -> Text|str.

        Keys are normalized to non-empty strings; values may be Text or str.
        """
        new_map: Dict[str, Choice] = {}
        for k_in, v_in in choices.items():
            k = str(k_in).strip()
            if not k:
                raise ValueError("Choice key must be a non-empty string")
            if k in new_map:
                raise ValueError(f"Duplicate choice key: {k}")
            v = v_in if isinstance(v_in, Text) else str(v_in)
            new_map[k] = Choice(k, v)
        self._choices = new_map
        return self

    # Removed add_choices/add_choice in strict API

    # Global constraints
    def set_constraints(self, mapping: Mapping[str, "Constraint"]) -> "MetaChoice":
        """Replace all global constraints from a mapping id -> Constraint.

        The Constraint.id field is ignored for keying purposes; mapping key is used.
        """
        self._global_groups.clear()
        for cid, c in mapping.items():
            cons = BaseConstraint(id=cid, members=c.members, min=c.min, max=c.max, description=None)
            self._validate_and_store_global(cons)
        return self
        return self

    def _validate_and_store_global(self, constraint: BaseConstraint) -> None:
        if constraint.id == CORRECT_GROUP_ID:
            raise ValueError("'__correct__' is reserved; use Stem.set_choices_correct() instead")
        missing: List[str] = []
        for m in constraint.members:
            key = str(m).strip()
            if key not in self._choices:
                missing.append(key)
        if missing:
            raise ValueError(f"Global constraint '{constraint.id}' has members not in pool: {sorted(missing)}")
        self._global_groups[constraint.id] = constraint

    def add_constraint(self, *members: str, min: int = 0, max: Optional[int] = None, id: Optional[str] = None) -> "MetaChoice":
        """Add a global constraint (strict form): members + bounds; optional id."""
        cid = str(id or f"__auto_{len(self._global_groups)+1}")
        cons = BaseConstraint(id=cid, members=frozenset(str(m).strip() for m in members), min=int(min), max=None if max is None else int(max), description=None)
        self._validate_and_store_global(cons)
        return self

    # Stem creation
    def add_stem(self, key: str, text: Union[Text, str], *, correct: Iterable[str], constraints: Mapping[str, "Constraint"] = {}) -> Stem:
        """Register a stem strictly via key/text, correctness, and local constraints."""
        stem = Stem(key=str(key), text=str(text) if not isinstance(text, Text) else text.text)
        stem.set_choices_correct(correct)
        for cid, c in (constraints or {}).items():
            cons = BaseConstraint(id=cid, members=c.members, min=c.min, max=c.max, description=None)
            stem.add_constraint(cons)
        self._stems.append(stem)
        return stem

    def _constraints_for_stem(self, stem: Stem) -> List[BaseConstraint]:
        groups: List[BaseConstraint] = list(self._global_groups.values()) + list(stem.local_groups)
        return self._materialize_constraints(groups)

    def _materialize_constraints(self, groups: Sequence[BaseConstraint]) -> List[BaseConstraint]:
        out: List[BaseConstraint] = []
        for g in groups:
            members: Set[str] = set()
            for m in g.members:
                key = m.key if isinstance(m, Choice) else str(m).strip()
                if key not in self._choices:
                    raise ValueError(f"Group {g.id} has member not in pool: {key}")
                members.add(key)
            out.append(BaseConstraint(id=g.id, members=frozenset(members), min=g.min, max=g.max, description=g.description))
        return out

    def _adjust_constraints_for_correct(
        self,
        raw_groups: Sequence[BaseConstraint],
        *,
        override_minmax: Optional[tuple[int, int]] | None,
    ) -> tuple[list[BaseConstraint], set[str]]:
        """Return adjusted constraints and the set of correct member keys.

        If override_minmax is provided, the correct group's min/max are overridden.
        When overriding to (1,1), enforce generate_singlechoice's invariant that the
        original correct group must not demand more than one correct (min<=1).
        """
        adjusted: List[BaseConstraint] = []
        correct_members: Set[str] = set()
        saw_correct = False
        for g in raw_groups:
            if g.id == CORRECT_GROUP_ID:
                saw_correct = True
                correct_members.update(g.members)
                if override_minmax is None:
                    adjusted.append(g)
                else:
                    if override_minmax == (1, 1) and g.min > 1:
                        raise ValueError("generate_singlechoice requires correct-group min<=1")
                    m0, m1 = override_minmax
                    adjusted.append(BaseConstraint(id=g.id, members=g.members, min=m0, max=m1, description=g.description))
            else:
                adjusted.append(g)
        if not saw_correct:
            raise ValueError("No correct group defined for stem; call set_choices_correct")
        return adjusted, correct_members

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
        out: List[List[str]] = [sorted(s, key=pos.get) for s in it]
        if not out:
            raise ValueError("No feasible subset satisfying constraints; adjust group bounds or n")
        return out

    def _build_multichoice(
        self,
        stem: Stem,
        subset: Sequence[str],
        correct_members: Set[str],
        prototype: Optional[MultiChoice] = None,
    ) -> MultiChoice:
        pool = self._choices
        correct = [k for k in subset if k in correct_members]
        wrong = [k for k in subset if k not in correct_members]
        k = len(correct)
        if k <= 0:
            raise RuntimeError("Invariant violated: subset must include at least one correct")
        per = 100.0 / k
        q = deepcopy(prototype) if prototype is not None else MultiChoice(name=stem.key)
        q.name = stem.key
        q.set_questiontext(stem.text)
        q.answers = []
        for ck in correct:
            q.add_answer(Answer.from_text(pool[ck].text, fraction=per))
        for wk in wrong:
            q.add_answer(Answer.from_text(pool[wk].text, fraction=0.0))
        q.validate()
        return q

    def _build_singlechoice(
        self,
        stem: Stem,
        subset: Sequence[str],
        correct_members: Set[str],
        prototype: Optional[SingleChoice] = None,
    ) -> SingleChoice:
        pool = self._choices
        correct = [k for k in subset if k in correct_members]
        if len(correct) != 1:
            raise RuntimeError("Internal error: expected exactly one correct after constraint adjustment")
        chosen = correct[0]
        q = deepcopy(prototype) if prototype is not None else SingleChoice(name=stem.key)
        q.name = stem.key
        q.set_questiontext(stem.text)
        q.answers = []
        q.add_answer(Answer.from_text(pool[chosen].text, fraction=100.0))
        for wk in (k for k in subset if k != chosen):
            q.add_answer(Answer.from_text(pool[wk].text, fraction=0.0))
        q.validate()
        return q

    def _generate_generic(
        self,
        *,
        n: int,
        limit: int,
        seed: Optional[int],
        randomize_order: bool,
        randomize_branch: bool,
        correct_bounds: Optional[tuple[int, int]],
        builder,
        prototype: Optional[Union[MultiChoice, SingleChoice]] = None,
    ) -> QuestionGroup:
        if not self._choices:
            raise ValueError("Choice pool is empty; call set_choices()/add_choice() first")
        if limit <= 0:
            raise ValueError("limit must be >= 1")
        out: List[Any] = []
        base_seed = int(seed) if seed is not None else None
        pool_items: List[str] = list(self._choices.keys())
        for idx, stem in enumerate(self._stems):
            raw_groups = self._constraints_for_stem(stem)
            adjusted, correct_members = self._adjust_constraints_for_correct(raw_groups, override_minmax=correct_bounds)
            stem_seed = None if base_seed is None else (base_seed + idx)
            subsets = self._pick_subsets(
                pool=pool_items,
                groups=adjusted,
                n=n,
                seed=stem_seed,
                limit=limit,
                randomize_order=randomize_order,
                randomize_branch=randomize_branch,
            )
            for subset in subsets:
                out.append(builder(stem, subset, correct_members, prototype))
        return QuestionGroup(variants=out)

    def generate_multichoice(
        self,
        *,
        n: int,
        limit: int = 1,
        seed: Optional[int] = None,
        randomize_order: bool = True,
        randomize_branch: bool = True,
        nc: Optional[int | tuple[int, int]] = None,
        prototype: Optional[MultiChoice] = None,
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
        - prototype: an optional MultiChoice with desired defaults (e.g., shuffle, labels,
              combined feedback). It is deep-copied per variant; answers are replaced.
        """
        bounds: Optional[tuple[int, int]]
        if nc is None:
            bounds = None
        else:
            if isinstance(nc, int):
                kmin = kmax = int(nc)
            else:
                a, b = nc
                kmin, kmax = int(min(a, b)), int(max(a, b))
            if kmin < 0 or kmax < 0 or kmin > kmax or kmax > n:
                raise ValueError("Invalid nc bounds; must satisfy 0 <= min <= max <= n")
            bounds = (kmin, kmax)
        return self._generate_generic(
            n=n,
            limit=limit,
            seed=seed,
            randomize_order=randomize_order,
            randomize_branch=randomize_branch,
            correct_bounds=bounds,
            builder=self._build_multichoice,
            prototype=prototype,
        )

    def generate_singlechoice(
        self,
        *,
        n: int,
        limit: int = 1,
        seed: Optional[int] = None,
        randomize_order: bool = True,
        randomize_branch: bool = True,
        prototype: Optional[SingleChoice] = None,
    ) -> QuestionGroup:
        """Generate SingleChoice questions for each stem and return a QuestionGroup.

        Behavior
        - Internally tightens the reserved "__correct__" group bounds to exactly one
          (min=1, max=1) for sampling. If a stem config has min>1, raises ValueError.
        """
        return self._generate_generic(
            n=n,
            limit=limit,
            seed=seed,
            randomize_order=randomize_order,
            randomize_branch=randomize_branch,
            correct_bounds=(1, 1),
            builder=self._build_singlechoice,
            prototype=prototype,
        )
