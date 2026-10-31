# Jinja environment and filter setup for Moodle writer
from __future__ import annotations

import re
from typing import Optional

from jinja2 import Environment, FileSystemLoader, PackageLoader, ChoiceLoader

from .utils import escape_markdown_math


def make_env(user_dir: Optional[str], kind: str) -> Environment:
    """
    kind: 'xml' or 'html'
    Search order:
      1) user-provided templates_dir (if any)
      2) built-in Moodle templates in package questionsafe.writer.moodle.templates
    """
    loaders = []
    if user_dir:
        loaders.append(FileSystemLoader(user_dir))
    loaders.append(PackageLoader("questionsafe.writer.moodle", "templates"))

    env = Environment(
        loader=ChoiceLoader(loaders),
        autoescape=(kind == "html"),
        trim_blocks=False,
        lstrip_blocks=True,
    )

    # filters
    def cdata(s: Optional[str]) -> str:
        if s is None:
            return "<![CDATA[]]>"
        return f"<![CDATA[{s}]]>"

    env.filters["cdata"] = cdata

    def moodle_text(s: Optional[str], fmt: Optional[str]) -> Optional[str]:
        """Text as Moodle should store it for format fmt."""
        return escape_markdown_math(s) if s and fmt == "markdown" else s

    env.filters["moodle_text"] = moodle_text

    def xmlbool(b: object) -> str:
        return "true" if (b is True or str(b).lower() in ("true", "1")) else "false"

    env.filters["xmlbool"] = xmlbool

    VALID = {"abc", "ABCD", "123", "iii", "III", "none"}

    def numscheme(s: Optional[str]) -> str:
        s = (s or "none").strip()
        return s if s in VALID else "none"

    def slug(s: str) -> str:
        s = (s or "").strip().lower()
        s = re.sub(r"\s+", "-", s)  # spaces -> hyphen
        s = re.sub(r"[^\w\-]+", "-", s)  # non-word -> hyphen
        s = re.sub(r"-{2,}", "-", s).strip("-")
        return s or "category"

    env.filters["numscheme"] = numscheme
    env.filters["slug"] = slug

    return env
