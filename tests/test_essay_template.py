"""Moodle shows the essay response template as-is (no format_text)."""
from __future__ import annotations

import textwrap

from lxml import etree

from questionsafe import Q, Reader, Text, render_xml

MD = r"Intro: **fill** \( a*b \)"


def _template(xml: bytes) -> tuple[str, str]:
    el = etree.fromstring(xml).find("question[@type='essay']/responsetemplate")
    return el.get("format"), el.findtext("text")


def _read(tmp_path, template: str):
    p = tmp_path / "e.md"
    p.write_text(
        textwrap.dedent(
            f"""\
            ---
            type: essay
            name: E
            response:
              textarea:
                template: {template}
            ---

            Explain.
            """
        ),
        encoding="utf-8",
    )
    return Reader(p).read()


def test_template_is_written_without_math_escaping():
    q = Q.Essay(name="E", questiontext="Explain.").set_response_template(Text(MD, format="markdown"))
    assert _template(render_xml([q])) == ("markdown", MD)


def test_reader_template_text_and_format(tmp_path):
    q = _read(tmp_path, "{text: 'Intro: **fill**', format: markdown}")
    assert q.response.textarea.template == Text("Intro: **fill**", format="markdown")


def test_reader_template_string_does_not_inherit_markdown(tmp_path):
    q = _read(tmp_path, "'Intro: **fill**'")
    assert q.response.textarea.template == Text("Intro: **fill**", format="html")


def test_essay_text_mapping_from_python():
    q = Q.Essay(name="E").set_response_template({"text": "T", "format": "plain"})
    q.set_graderinfo({"text": "G", "format": "markdown"})
    assert q.response.textarea.template == Text("T", format="plain")
    assert (q.graderinfo.text, q.graderinfo.format) == ("G", "markdown")
