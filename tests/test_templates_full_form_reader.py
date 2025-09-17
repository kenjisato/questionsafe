import textwrap
from pathlib import Path

import pytest

from questionsafe import Reader


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "questionsafe" / "cli" / "templates"


def _render_template(template_path: Path, *, name: str) -> str:
    text = template_path.read_text(encoding="utf-8")
    # Minimal rendering: replace the only variable we use in these templates
    return text.replace("{{ name }}", name)


def _setup_cloze_embeds(base_dir: Path) -> None:
    # Create minimal embedded questions referenced by cloze-full.md.j2
    (base_dir / "your_singlechoice.md").write_text(
        textwrap.dedent(
            """
            ---
            type: singlechoice
            name: gap1
            choices:
              correct: [Tokyo]
              wrong: [Osaka, Kyoto, Kanagawa]
            ---

            
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (base_dir / "your_multichoice.md").write_text(
        textwrap.dedent(
            """
            ---
            type: multichoice
            name: gap2
            choices:
              correct: [Shinagawa, Shinjuku]
              wrong: [Yokohama, Omiya]
            ---

            
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "template_filename, qname, setup",
    [
        ("singlechoice-full.md.j2", "Example/Single", None),
        ("multichoice-full.md.j2", "Example/Multi", None),
        ("truefalse-full.md.j2", "Example/TrueFalse", None),
        ("shortanswer-full.md.j2", "Example/Short", None),
        ("numerical-full.md.j2", "Example/Numerical", None),
        ("numerical_unit-full.md.j2", "Example/NumericalUnits", None),
        pytest.param(
            "cloze-full.md.j2",
            "Example/Cloze",
            _setup_cloze_embeds,
            id="cloze-full",
        ),
        # Reader does not currently implement 'essay' import; keep a sentinel to revisit later.
        ("essay-full.md.j2", "Example/Essay", None),
    ],
)
def test_full_templates_are_reader_readable(tmp_path: Path, template_filename: str, qname: str, setup):
    template_path = TEMPLATES_DIR / template_filename
    assert template_path.exists(), f"Missing template: {template_path}"

    # Optional per-template setup (e.g., CLOZE embedded files)
    if callable(setup):
        setup(tmp_path)

    rendered = _render_template(template_path, name=qname)
    out_path = tmp_path / template_filename.replace(".md.j2", ".md")
    out_path.write_text(rendered, encoding="utf-8")

    q = Reader(out_path).read()
    assert getattr(q, "name", None) == qname
