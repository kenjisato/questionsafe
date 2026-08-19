from __future__ import annotations
import textwrap
from pathlib import Path


def _write(tmp_path, rel, text: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return p


def test_reader_cloze_with_embedded_files(tmp_path):
    from questionsafe import Reader, Q

    # Create embedded questions
    _write(
        tmp_path,
        "schoice.md",
        """
        ---
        type: singlechoice
        name: gap1
        choices:
          correct: [Tokyo]
          wrong: [Osaka, Kyoto, Kanagawa]
        ---

        
        """,
    )
    _write(
        tmp_path,
        "mchoice.md",
        """
        ---
        type: multichoice
        name: gap2
        choices:
          correct: [Shinagawa, Shinjuku]
          wrong: [Yokohama, Omiya]
        ---

        
        """,
    )

    # Cloze top-level
    cloze_path = _write(
        tmp_path,
        "cloze.md",
        """
        ---
        name: Japan/Cities
        type: cloze
        cloze:
          gap1: schoice.md
          gap2:
            - file: mchoice.md
            - orientation: h
            - weight: 2
        ---

        The capital of Japan is {{ gap1 }}. 
        Choose stations in Tokyo.
        {{  gap2  }}
        """,
    )

    q_yaml = Reader(cloze_path).read()

    # Embedded fragments are not standalone-valid (empty questiontext), so skip validation
    gap1 = Reader(tmp_path / "schoice.md").read(validate=False).set_name("gap1")
    gap2 = Reader(tmp_path / "mchoice.md").read(validate=False).set_name("gap2")
    q_py = (
        Q.Cloze("Japan/Cities")
        .ask("The capital of Japan is {{ gap1 }}. \nChoose stations in Tokyo.\n{{  gap2  }}")
        .embed_question(gap1)
        .embed_question(gap2, orientation="h", weight=2)
    )

    assert q_yaml.compile_text() == q_py.compile_text()


def test_reader_cloze_without_mapping_uses_raw_tokens(tmp_path):
    from questionsafe import Reader, Q

    cloze_path = _write(
        tmp_path,
        "cloze_raw.md",
        """
        ---
        name: Japan/Cities
        type: cloze
        ---

        The capital of Japan is {1:MC:=Tokyo~Osaka~Kyoto~Kanagawa}. 
        Choose stations in Tokyo.
        {2:MRH:=Shinagawa~=Shinjuku~Yokohama~Omiya}
        """,
    )

    q_yaml = Reader(cloze_path).read()

    q_py = Q.Cloze("Japan/Cities").ask(
        "The capital of Japan is {1:MC:=Tokyo~Osaka~Kyoto~Kanagawa}. \nChoose stations in Tokyo.\n{2:MRH:=Shinagawa~=Shinjuku~Yokohama~Omiya}"
    )

    # No embedded mapping -> compile_text should just return the body unchanged
    assert q_yaml.compile_text() == q_py.compile_text()

