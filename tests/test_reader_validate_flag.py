from __future__ import annotations
import textwrap

import pytest


INVALID_MULTICHOICE = """
---
type: multichoice
name: Bad MC
answers:
  - text: Alpha
    fraction: 50
  - text: Beta
    fraction: 30
---

Pick some.
"""


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "q.md"
    p.write_text(textwrap.dedent(text).strip(), encoding="utf-8")
    return str(p)


def test_reader_validate_true_raises_on_invalid_multichoice(tmp_path):
    from questionsafe import Reader

    p = _write(tmp_path, INVALID_MULTICHOICE)
    with pytest.raises(ValueError):
        Reader(p).read(validate=True)


def test_reader_validate_false_returns_invalid_question(tmp_path):
    from questionsafe import Reader, Q

    p = _write(tmp_path, INVALID_MULTICHOICE)
    q = Reader(p).read(validate=False)
    assert isinstance(q, Q.MultiChoice)
    assert q.name == "Bad MC"
