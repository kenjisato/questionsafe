# Moodle writer: context registry and renderers
from __future__ import annotations
from functools import singledispatch
from typing import List, Dict, Any
from pathlib import Path
from ._templating import make_env
from .._common import to_context as _to_ctx, title_of, write_bytes, write_text


# --- ctx registry (Moodle-specific) ---
@singledispatch
def ctx(obj: object) -> Dict[str, Any]:
    raise TypeError(f"No context builder for {type(obj).__name__}")


DefQuestions = Any


def to_context(obj: DefQuestions) -> List[Dict[str, Any]]:
    return _to_ctx(obj, ctx)


# --- template-driven renderers ---


def render_xml(obj: DefQuestions, *, templates_dir: str | None = None) -> bytes:
    questions = to_context(obj)
    env = make_env(templates_dir, kind="xml")
    tpl = env.get_template("_quiz.xml.j2")
    xml = tpl.render(questions=questions)
    return xml.encode("utf-8")


def render_html(
    obj: DefQuestions, *, title: str | None = None, templates_dir: str | None = None
) -> str:
    qs = to_context(obj)
    if title is None:
        title = title_of(obj, default="")
    env = make_env(templates_dir, kind="html")
    layout = env.get_template("_quiz.html.j2")
    parts: list[str] = []
    for n in qs:
        frag = env.get_template(f"{n['type']}.html.j2").render(n=n)
        parts.append(frag)
    return layout.render(title=title, body_html="\n".join(parts))


# --- file writers ---


def write_xml(
    obj: DefQuestions, path: Path | str, *, templates_dir: str | None = None
) -> Path:
    data = render_xml(obj, templates_dir=templates_dir)
    return write_bytes(data, path)


def write_html(
    obj: DefQuestions,
    path: Path | str,
    *,
    title: str | None = None,
    templates_dir: str | None = None,
) -> Path:
    html = render_html(obj, title=title, templates_dir=templates_dir)
    return write_text(html, path, encoding="utf-8")
