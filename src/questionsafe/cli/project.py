
from __future__ import annotations
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from ._common import console

from ..importers import Reader
from ..writer import render_xml
from ._common import (
    available_template_names,
    questions_root_from_config,
    resolve_out_path,
    package_templates_dir,
    render_template,
)



def add_project_commands(app: typer.Typer) -> None:
    @app.command()
    def render(
        file: str = typer.Argument(..., help="Markdown file with YAML front matter"),
        out: Optional[str] = typer.Option(
            None,
            "--out",
            help="Output XML file path; if omitted, prints XML to stdout",
        ),
        templates_dir: Optional[str] = typer.Option(
            None, "--templates-dir", help="Custom templates directory (optional)"
        ),
    ):
        """Render a single Markdown question to Moodle XML (single-question <quiz>)."""
        p = Path(file)
        if not p.exists() or not p.is_file():
            console.print(f"[red]File not found: {p}[/red]")
            raise typer.Exit(1)
        try:
            q = Reader(p).read()
        except Exception as e:
            console.print(f"[red]Failed to parse {p}[/red]: {e}")
            raise typer.Exit(1) from None
        xml_bytes = render_xml([q], templates_dir=templates_dir)
        if out is None:
            import sys as _sys
            _sys.stdout.buffer.write(xml_bytes)
        else:
            out_path = Path(out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(xml_bytes)
            console.print(f"[green]Wrote XML -> {out_path}[/green]")

    @app.command()
    def create(
        path: Optional[str] = typer.Argument(
            None,
            help="Output Markdown file path (e.g., questions/new.md). If omitted, interactive prompt.",
        ),
        name: Optional[str] = typer.Option(
            None,
            "--name",
            "-n",
            help="Question name (used in YAML). If omitted, interactive prompt.",
        ),
        qtype: Optional[str] = typer.Option(
            None,
            "--type",
            "-t",
            help="Question template name (derived from *.md.j2). If omitted, interactive prompt.",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            "-f",
            help="Overwrite existing file without confirmation (non-interactive).",
        ),
    ):
        """Create a Markdown question file from a template."""
        interactive = path is None or name is None or qtype is None
        cwd = Path.cwd()
        names, base_dir, is_user = available_template_names(cwd)
        if not names:
            console.print("[red]No templates found. Ensure package templates are installed or configure project.templates in questionsafe.yml[/red]")
            raise typer.Exit(1)
        qroot = questions_root_from_config(cwd)
        if interactive:
            try:
                from InquirerPy import inquirer  # type: ignore
            except Exception as e:  # pragma: no cover
                console.print("[red]InquirerPy is required for interactive mode. Install and retry.[/red]")
                raise typer.Exit(1) from e
            # Show just a filename by default, regardless of questions root
            default_display = "new-question.md"
            path = inquirer.text(message="File path:", default=default_display).execute()
            if not path:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(1)
            # Normalize to avoid duplicating the questions root when user typed 'questions/...'
            if qroot is not None:
                qp = Path(path)
                if not qp.is_absolute() and qp.parts and qp.parts[0] == qroot.name:
                    qp = Path(*qp.parts[1:])
                    path = str(qp)
            p = resolve_out_path(path, qroot)
            default_name = p.stem
            name = inquirer.text(message="Question name:", default=default_name).execute()
            if not name:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(1)
            selection = inquirer.select(message="Choose a question type:", choices=names).execute()
            if not selection:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(1)
            qtype = str(selection)
            if p.exists():
                ok = inquirer.confirm(message=f"{p} exists. Overwrite?", default=False).execute()
                if not ok:
                    console.print("[yellow]Aborted (file exists).[/yellow]")
                    raise typer.Exit(1)
        else:
            assert path is not None and name is not None and qtype is not None
            # Normalize to avoid duplicating the questions root when user passed 'questions/...'
            if qroot is not None:
                qp = Path(path)
                if not qp.is_absolute() and qp.parts and qp.parts[0] == qroot.name:
                    qp = Path(*qp.parts[1:])
                    path = str(qp)
            p = resolve_out_path(path, qroot)
            qtype = qtype.lower()
            if qtype not in names:
                raise typer.BadParameter(f"Unsupported type: {qtype}. Choose from {', '.join(names)}")
            if p.exists() and not force:
                console.print(f"[red]Refusing to overwrite existing file: {p}[/red]")
                console.print("Use --force to overwrite or run without args for interactive confirm.")
                raise typer.Exit(1)
        assert name is not None and qtype is not None
        user_dir = base_dir if is_user else None
        content = render_template(qtype, context={"name": name}, user_dir=user_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        console.print(f"[green]Created {p}[/green]")

    @app.command()
    def init(
        dir: Optional[str] = typer.Argument(
            None,
            help="Directory to scaffold into (defaults to current directory)",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            "-f",
            help="Overwrite questionsafe.yml if it exists and copy templates over existing files.",
        ),
    ):
        """Scaffold a questionsafe project directory with templates and config."""
        base = Path(dir) if dir is not None else Path.cwd()
        base.mkdir(parents=True, exist_ok=True)
        questions_dir = base / "questions"
        templates_dir = base / "templates"
        questions_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = base / "questionsafe.yml"
        cfg_text = (
            "project:\n"
            "  questions: ./questions\n"
            "  templates: ./templates\n"
        )
        if cfg_path.exists() and not force:
            console.print("[yellow]questionsafe.yml exists; skipping (use --force to overwrite)[/yellow]")
        else:
            cfg_path.write_text(cfg_text, encoding="utf-8")
        pkg_dir = package_templates_dir()
        copied = 0
        for p in pkg_dir.iterdir():
            if p.is_file() and p.suffix == ".j2" and p.name.endswith(".md.j2"):
                dest = templates_dir / p.name
                if dest.exists() and not force:
                    continue
                dest.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
                copied += 1
        console.print(f"[green]Initialized project at {base}[/green]")
        console.print(f"Templates: {copied} files copied to {templates_dir}")

    @app.command()
    def build():
        raise NotImplementedError

    @app.command()
    def validate(
        paths: Annotated[
            Optional[list[str]],
            typer.Argument(
                help="Markdown question files or directories (searched recursively for *.md). "
                "Defaults to the project questions directory from questionsafe.yml.",
            ),
        ] = None,
        target: Optional[str] = typer.Option(
            None,
            "--target",
            help="Target Moodle version like '4.5'; flags version-gated features.",
        ),
        templates_dir: Optional[str] = typer.Option(
            None, "--templates-dir", help="Custom templates directory (optional)"
        ),
    ):
        """Validate questions: model rules, XML well-formedness, optional version check."""
        from lxml import etree

        from ..writer.moodle import check_target, parse_version

        if target is not None:
            try:
                parse_version(target)
            except ValueError as e:
                raise typer.BadParameter(str(e)) from None

        # Collect files
        files: list[Path] = []
        if paths:
            for raw in paths:
                p = Path(raw)
                if p.is_dir():
                    files.extend(sorted(p.rglob("*.md")))
                elif p.is_file():
                    files.append(p)
                else:
                    console.print(f"[red]Path not found: {p}[/red]", soft_wrap=True)
                    raise typer.Exit(1)
        else:
            qroot = questions_root_from_config(Path.cwd())
            if qroot is None or not qroot.is_dir():
                console.print(
                    "[red]No paths given and no questions directory configured "
                    "(questionsafe.yml: project.questions).[/red]",
                    soft_wrap=True,
                )
                raise typer.Exit(1)
            files = sorted(qroot.rglob("*.md"))

        errors = 0
        parsed: list[tuple[Path, Any]] = []
        for f in files:
            try:
                reader = Reader(f)
                if reader.question_type() == "metachoice":
                    # Template-level checks only; XML exists after generation,
                    # whose parameters (n, seed, ...) belong to the exam build.
                    reader.read_metachoice(validate=True)
                    console.print(
                        f"[green]OK[/green] {f} [dim](metachoice template)[/dim]",
                        soft_wrap=True,
                    )
                    continue
                q = reader.read(validate=True)
                etree.fromstring(render_xml([q], templates_dir=templates_dir))
            except Exception as e:
                errors += 1
                console.print(f"[red]ERROR[/red] {f}: {e}", soft_wrap=True)
                continue
            parsed.append((f, q))
            console.print(f"[green]OK[/green] {f}", soft_wrap=True)

        if target is not None:
            for f, q in parsed:
                for msg in check_target([q], target):
                    errors += 1
                    console.print(f"[red]TARGET[/red] {f}: {msg}", soft_wrap=True)

        n = len(files)
        console.print(
            f"{n} file{'s' if n != 1 else ''} checked, {errors} error{'s' if errors != 1 else ''}",
            soft_wrap=True,
        )
        if errors:
            raise typer.Exit(1)

    @app.command()
    def preview():
        raise NotImplementedError
