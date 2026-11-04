"""Image references in question texts: Markdown `![alt](src)` and HTML `<img>` (#3)."""
from __future__ import annotations

import re
from typing import Callable

_TAG = r"(?P<tag><img\b[^>]*>)"
# A Markdown src may be wrapped in <...>, which a path with spaces needs.
_MD = (
    r"(?P<md>!\[(?P<alt>[^\]]*)\]\(\s*(?:<(?P<src_a>[^>]*)>|(?P<src>[^\s)]+))"
    r"(?:\s+(?P<title>\"[^\"]*\"|'[^']*'))?\s*\))"
)
_CODE = r"(?P<code>```.*?```|`[^`\n]*`)"
_IMAGE = {
    "html": re.compile(_TAG, re.IGNORECASE),
    "markdown": re.compile(f"{_CODE}|{_MD}|{_TAG}", re.DOTALL | re.IGNORECASE),
}
_REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]+:|//|@@PLUGINFILE@@)", re.IGNORECASE)


def _attr(name: str) -> re.Pattern[str]:
    return re.compile(rf"""\s{name}\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)


_SRC, _ALT, _TITLE = _attr("src"), _attr("alt"), _attr("title")


def is_local(src: str) -> bool:
    return bool(src) and not _REMOTE.match(src)


def sub_images(text: str, fmt: str, fn: Callable[[str], str], *, alt: str | None = None) -> str:
    """Replace the src of each local image with fn(src).

    Markdown texts are searched for both forms (code excluded), HTML texts for `<img>`;
    other formats are returned unchanged. With alt given, each local image gets that
    alt text and loses its title.
    """
    pattern = _IMAGE.get(fmt)
    if pattern is None:
        return text

    def md(m: re.Match[str]) -> str:
        src = m["src"] if m["src_a"] is None else m["src_a"]
        if not is_local(src):
            return m[0]
        new = fn(src)
        new = f"<{new}>" if re.search(r"\s", new) else new
        title = f" {m['title']}" if m["title"] and alt is None else ""
        return f"![{m['alt'] if alt is None else alt}]({new}{title})"

    def tag(m: re.Match[str]) -> str:
        t = m[0]
        src = _SRC.search(t)
        if not src or not is_local(src[2]):
            return t
        t = t[: src.start(2)] + fn(src[2]) + t[src.end(2) :]
        if alt is not None:
            t = _ALT.sub("", _TITLE.sub("", t))
            end = _SRC.search(t).end()
            t = f'{t[:end]} alt="{alt}"{t[end:]}'
        return t

    def repl(m: re.Match[str]) -> str:
        if m.groupdict().get("md"):
            return md(m)
        if m["tag"]:
            return tag(m)
        return m[0]

    return pattern.sub(repl, text)
