"""Embed local images as files of the Moodle text field that shows them (#3)."""
from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ...base._images import sub_images

RASTER = (".png", ".jpg", ".jpeg", ".gif", ".webp")
# Every image choice gets the same alt text: a descriptive one would give the answer away.
CHOICE_ALT = "Choice image"


@dataclass(frozen=True)
class Embedded:
    text: str
    files: list[dict[str, str]] = field(default_factory=list)  # {"name", "data" (base64)}


@lru_cache(maxsize=256)
def _load(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext == ".svg":
        raise ValueError(
            f"{path}: SVG images are not supported (their text is visible in the page source); "
            "use PNG, JPEG, GIF, or WebP"
        )
    if ext not in RASTER:
        raise ValueError(f"{path}: unsupported image type; use PNG, JPEG, GIF, or WebP")
    try:
        data = path.read_bytes()
    except OSError as e:
        raise ValueError(f"image not found: {path}") from e
    # The name is the content hash, so the author's file name never reaches the student.
    return hashlib.sha256(data).hexdigest()[:12] + ext, base64.b64encode(data).decode("ascii")


def embed_images(text: str | None, fmt: str | None, *, alt: str | None = None) -> Embedded:
    """Rewrite local image references to @@PLUGINFILE@@ and collect the files.

    Relative paths resolve against the current directory; the Markdown reader has
    already made them absolute, relative to the question file.
    """
    if not text:
        return Embedded(text or "")
    files: dict[str, str] = {}

    def fn(src: str) -> str:
        name, data = _load(Path(src).expanduser().resolve())
        files[name] = data
        return f"@@PLUGINFILE@@/{name}"

    new = sub_images(text, fmt or "html", fn, alt=alt)
    return Embedded(new, [{"name": n, "data": d} for n, d in files.items()])


def hashed_order(answers: list[dict], shuffle: bool) -> list[dict]:
    """Order shuffled choices by a hash of their text instead of the authoring order.

    Moodle numbers answers in XML order and shows the number in image URLs; authors
    often write the correct choice first. Hashing the embedded text keeps the order
    independent of where the question file lives.
    """
    if not shuffle:
        return answers

    def key(a: dict) -> str:
        text = embed_images(a["text"], a.get("answer_format"), alt=CHOICE_ALT).text
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    return sorted(answers, key=key)
