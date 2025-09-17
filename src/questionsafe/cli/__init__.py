from __future__ import annotations
import typer

from .project import add_project_commands
from .course import course_app

app = typer.Typer(add_completion=False, help="A Moodle Quiz Composer")

# Wire up subcommands
add_project_commands(app)
app.add_typer(course_app, name="course")

__all__ = ["app"]

