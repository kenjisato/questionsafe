from __future__ import annotations
from pathlib import Path
from typing import Optional

import typer

from ._common import (
    questions_root_from_config,
    get_current_course,
    set_current_course,
    console,
)

course_app = typer.Typer(help="Manage courses and coverage analysis")


@course_app.command("init")
def course_init(
    course_id: str = typer.Argument(..., help="Course identifier (e.g., ECON101)"),
    title: Optional[str] = typer.Option(None, "--title", help="Course title (optional)"),
    dir: Optional[str] = typer.Option(None, "--dir", help="Base directory (defaults to CWD)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
):
    base = Path(dir) if dir is not None else Path.cwd()
    cdir = base / "courses" / course_id
    cdir.mkdir(parents=True, exist_ok=True)
    qroot = questions_root_from_config(base) or (base / "questions")
    try:
        qroot_rel = str(qroot.relative_to(base))
    except Exception:
        qroot_rel = str(qroot)
    topics_csv = (
        "group,description\n"
        "A,General\n"
        "B,SNA\n"
    )
    objectives_csv = (
        "group,index,description\n"
        "A,1,Example objective A1\n"
        "A,2,Example objective A2\n"
        "B,1,Example objective B1\n"
    )
    relationships_csv = (
        "group,index,question,difficulty\n"
        "A,1,unit1/q1.md,1\n"
    )
    readme = (
        f"# Course {course_id}\n\n"
        f"Title: {title or course_id}\n\n"
        f"Questions root: {qroot_rel}\n\n"
        "Edit topics.csv and objectives.csv to define objectives, then add rows to relationships.csv to map questions with difficulty.\n"
    )
    def _write(p: Path, content: str) -> None:
        if p.exists() and not force:
            return
        p.write_text(content, encoding="utf-8")
    _write(cdir / "topics.csv", topics_csv)
    _write(cdir / "objectives.csv", objectives_csv)
    _write(cdir / "relationships.csv", relationships_csv)
    _write(cdir / "README.md", readme)
    console.print(f"[green]Initialized course at {cdir}[/green]")


@course_app.command("coverage")
def course_coverage(
    course_id: Optional[str] = typer.Argument(None, help="Course ID (defaults to current)"),
    dir: Optional[str] = typer.Option(None, "--dir", help="Base directory (defaults to CWD)"),
):
    from ..analysis.coverage import analyze_csv_course
    base = Path(dir) if dir is not None else Path.cwd()
    qroot = questions_root_from_config(base) or (base / "questions")
    cid = course_id or get_current_course(base)
    if not cid:
        console.print("[red]No course specified and no current course set. Use 'questionsafe course checkout <ID>' or pass an ID.")
        raise typer.Exit(1)
    cdir = base / "courses" / cid
    if not cdir.exists():
        console.print(f"[red]Course directory not found: {cdir}[/red]")
        raise typer.Exit(1)
    try:
        report = analyze_csv_course(cdir, questions_root=qroot)
    except Exception as e:
        console.print(f"[red]Failed to analyze coverage[/red]: {e}")
        raise typer.Exit(1) from None
    console.print(report.to_text(), markup=False)


@course_app.command("checkout")
def course_checkout(course_id: str = typer.Argument(..., help="Course ID to set as current")):
    base = Path.cwd()
    cdir = base / "courses" / course_id
    if not cdir.exists():
        console.print(f"[red]Course not found: {cdir}[/red]")
        raise typer.Exit(1)
    set_current_course(base, course_id)
    console.print(f"[green]Set current course to {course_id}[/green]")


@course_app.command("list")
def course_list(dir: Optional[str] = typer.Option(None, "--dir", help="Base directory (defaults to CWD)")):
    base = Path(dir) if dir is not None else Path.cwd()
    croot = base / "courses"
    items = []
    if croot.exists():
        for p in sorted(croot.iterdir()):
            if p.is_dir():
                items.append(p.name)
    cur = get_current_course(base)
    if not items:
        console.print("No courses found.")
        return
    console.print("Courses:")
    for name in items:
        mark = " *" if cur == name else ""
        console.print(f"- {name}{mark}")


@course_app.command("objectives")
def course_objectives(course_id: Optional[str] = typer.Argument(None), dir: Optional[str] = typer.Option(None, "--dir")):
    from ..analysis.coverage import ObjectivesIndex
    base = Path(dir) if dir is not None else Path.cwd()
    cid = course_id or get_current_course(base)
    if not cid:
        console.print("[red]Specify a course ID or set current course with 'course checkout'.")
        raise typer.Exit(1)
    cdir = base / "courses" / cid
    try:
        idx = ObjectivesIndex.from_csv(cdir)
    except Exception as e:
        console.print(f"[red]Failed to read objectives[/red]: {e}")
        raise typer.Exit(1) from None
    lines: list[str] = []
    lines.append("Objectives:\n")
    gmap: dict[str, list[tuple[str, str]]] = {}
    for code, obj in idx.objectives.items():
        gmap.setdefault(obj.group, []).append((code, obj.text))
    for g in sorted(idx.groups.keys()):
        title = idx.groups.get(g, g)
        lines.append(f"{g}. {title}")
        for code, text in sorted(gmap.get(g, []), key=lambda x: x[0]):
            lines.append(f"  - {code}: {text}")
    console.print("\n".join(lines), markup=False)


@course_app.command("questions")
def course_questions(course_id: Optional[str] = typer.Argument(None), dir: Optional[str] = typer.Option(None, "--dir")):
    from ..analysis.coverage import _read_csv_relations  # type: ignore
    base = Path(dir) if dir is not None else Path.cwd()
    cid = course_id or get_current_course(base)
    if not cid:
        console.print("[red]Specify a course ID or set current course with 'course checkout'.")
        raise typer.Exit(1)
    cdir = base / "courses" / cid
    try:
        rels = _read_csv_relations(cdir)
    except Exception as e:
        console.print(f"[red]Failed to read relationships[/red]: {e}")
        raise typer.Exit(1) from None
    if not rels:
        console.print("No relationships found.")
        return
    console.print("Relationships:")
    for r in rels:
        lvl = r['difficulty'] if r['difficulty'] is not None else '-'
        console.print(f"- {r['objective']} -> {r['question']} (lvl {lvl})", markup=False)

