from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import csv
import frontmatter


@dataclass(frozen=True)
class Objective:
    code: str
    group: str
    text: str


@dataclass
class ObjectivesIndex:
    objectives: Dict[str, Objective]
    groups: Dict[str, str]  # group code -> description/title

    @classmethod
    def from_csv(cls, course_dir: Path) -> "ObjectivesIndex":
        topics_path = course_dir / "topics.csv"
        objectives_path = course_dir / "objectives.csv"
        if not topics_path.exists() or not objectives_path.exists():
            raise FileNotFoundError("topics.csv or objectives.csv not found in course directory")

        groups: Dict[str, str] = {}
        with topics_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                g = str(row.get("group", "")).strip()
                desc = str(row.get("description", "")).strip()
                if g:
                    groups[g] = desc or g

        objectives: Dict[str, Objective] = {}
        with objectives_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                g = str(row.get("group", "")).strip()
                idx = str(row.get("index", "")).strip()
                text = str(row.get("description", "")).strip()
                if not g or not idx or not text:
                    continue
                code = f"{g}{idx}"
                objectives[code] = Objective(code=code, group=g, text=text)
        if not objectives:
            raise ValueError("No objectives parsed from objectives.csv")
        return cls(objectives=objectives, groups=groups)


@dataclass
class QuestionRecord:
    path: Path
    name: str
    objectives: List[str]
    difficulty: int | None


@dataclass
class CoverageReport:
    objectives: ObjectivesIndex
    questions: List[QuestionRecord]

    def covered_codes(self) -> Dict[str, List[QuestionRecord]]:
        idx: Dict[str, List[QuestionRecord]] = {}
        for q in self.questions:
            for code in q.objectives:
                if code not in idx:
                    idx[code] = []
                idx[code].append(q)
        return idx

    def uncovered_codes(self) -> List[str]:
        covered = set(self.covered_codes().keys())
        all_codes = set(self.objectives.objectives.keys())
        return sorted(all_codes - covered)

    def group_stats(self) -> Dict[str, Tuple[int, int]]:
        covered = set(self.covered_codes().keys())
        stats: Dict[str, Tuple[int, int]] = {}
        for obj in self.objectives.objectives.values():
            g = obj.group
            cov = 1 if obj.code in covered else 0
            c, t = stats.get(g, (0, 0))
            stats[g] = (c + cov, t + 1)
        return stats

    def to_text(self) -> str:
        lines: List[str] = []
        lines.append("Coverage by Group:\n")
        gs = self.group_stats()
        keys = sorted(self.objectives.groups.keys() or gs.keys())
        for g in keys:
            c, t = gs.get(g, (0, 0))
            title = self.objectives.groups.get(g, g)
            pct = (100.0 * c / t) if t else 0.0
            lines.append(f"- {g}. {title}: {c}/{t} ({pct:.0f}%)")
        lines.append("")
        unc = self.uncovered_codes()
        if unc:
            lines.append("Uncovered Objectives:\n")
            for code in unc:
                obj = self.objectives.objectives.get(code)
                if obj:
                    lines.append(f"- {code}: {obj.text}")
            lines.append("")
        lines.append("Covered Objectives:\n")
        covered = self.covered_codes()
        for code in sorted(covered.keys()):
            obj = self.objectives.objectives.get(code)
            if not obj:
                continue
            lines.append(f"- {code}: {obj.text}")
            for q in covered[code]:
                diff = f" (lvl {q.difficulty})" if q.difficulty is not None else ""
                lines.append(f"  - {q.name}{diff} [{q.path}] ")
        return "\n".join(lines)


def _read_csv_relations(course_dir: Path) -> List[dict]:
    path = course_dir / "relationships.csv"
    if not path.exists():
        # also support relations.csv
        alt = course_dir / "relations.csv"
        if alt.exists():
            path = alt
        else:
            return []
    relations: List[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            g = str(row.get("group", "")).strip()
            idx = str(row.get("index", "")).strip()
            q = str(row.get("question", "")).strip()
            d = row.get("difficulty", None)
            if not g or not idx or not q:
                continue
            code = f"{g}{idx}"
            try:
                diff = int(d) if d not in (None, "") else None
            except Exception:
                diff = None
            relations.append({"objective": code, "question": q, "difficulty": diff})
    return relations


def _aggregate_questions_from_relations(
    relations: List[dict], *, questions_root: Path
) -> List[QuestionRecord]:
    agg: Dict[str, QuestionRecord] = {}
    for r in relations:
        code = r["objective"]
        qrel = r["question"]
        diff = r["difficulty"]
        p = (questions_root / qrel).resolve()
        key = str(p)
        if key not in agg:
            name = p.stem
            try:
                post = frontmatter.load(p)
                meta = dict(post.metadata or {})
                nm = meta.get("name")
                if isinstance(nm, str) and nm.strip():
                    name = nm
            except Exception:
                pass
            agg[key] = QuestionRecord(path=p, name=name, objectives=[], difficulty=None)
        rec = agg[key]
        if code not in rec.objectives:
            rec.objectives.append(code)
        if isinstance(diff, int):
            if rec.difficulty is None or diff > rec.difficulty:
                rec.difficulty = diff
    return list(agg.values())


# Public API used by CLI

def analyze_csv_course(course_dir: Path, *, questions_root: Path) -> CoverageReport:
    idx = ObjectivesIndex.from_csv(course_dir)
    relations = _read_csv_relations(course_dir)
    qs = _aggregate_questions_from_relations(relations, questions_root=questions_root)
    return CoverageReport(objectives=idx, questions=qs)
