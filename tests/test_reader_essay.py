from __future__ import annotations
import textwrap
from pathlib import Path


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_reader_essay_uses_config_variables_for_paths(tmp_path):
    from questionsafe import Reader, Q

    # CWD project
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    _write(tmp_path, "questionsafe.yml", "variables: { ROOT: ./data }")
    _write(tmp_path, "data/tpl.md", "TEMPLATE TEXT")
    _write(tmp_path, "data/gi.md", "GRADER INFO")

    q_path = _write(
        tmp_path,
        "essay.md",
        """
        ---
        type: essay
        name: E/Var
        response:
          textarea:
            format: editor
            lines: 5
            template:
              path: "$ROOT/tpl.md"
          attachments:
            count: 1
            required: true
        graderinfo:
          path: "$ROOT/gi.md"
        ---

        Please respond.
        """,
    )

    # Ensure cwd is tmp_path so Reader picks up questionsafe.yml there
    import os
    cwd0 = Path.cwd()
    try:
        os.chdir(tmp_path)
        q = Reader(q_path).read()
    finally:
        os.chdir(cwd0)

    assert isinstance(q, Q.Essay)
    # Validate noinline rule isn't triggered (we used editor format). Attachments set.
    assert q.response.attachments.count == 1 and q.response.attachments.required is True

