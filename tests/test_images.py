"""Local images in question text and choices are embedded as Moodle files (#3)."""
from __future__ import annotations

import base64
import hashlib
import textwrap

import pytest
from lxml import etree

from questionsafe import Q, Reader, Text, render_xml

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _png(path, salt: bytes = b""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG + salt)
    return path


def _name(data: bytes, ext: str = ".png") -> str:
    return hashlib.sha256(data).hexdigest()[:12] + ext


def _question(xml: bytes):
    return etree.fromstring(xml).find("question[@type='multichoice']")


def _files(el) -> dict[str, bytes]:
    return {f.get("name"): base64.b64decode(f.text) for f in el.findall("file")}


def test_question_text_image_is_embedded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _png(tmp_path / "fig.png")
    q = Q.SingleChoice(name="S", questiontext='<p><img src="fig.png" alt="Figure 1"></p>')
    q.set_choice_correct("A").set_choices_wrong("B")
    qt = _question(render_xml([q])).find("questiontext")
    name = _name(PNG)
    assert qt.findtext("text") == f'<p><img src="@@PLUGINFILE@@/{name}" alt="Figure 1"></p>'
    assert _files(qt) == {name: PNG}
    assert all(f.get("path") == "/" and f.get("encoding") == "base64" for f in qt.findall("file"))


def test_reader_resolves_images_relative_to_the_file(tmp_path, monkeypatch):
    qdir = tmp_path / "questions"
    _png(qdir / "img" / "curve.png")
    _png(qdir / "img" / "correct-shift-left.png", b"L")
    _png(qdir / "img" / "shift-right.png", b"R")
    md = qdir / "q.md"
    md.write_text(
        textwrap.dedent(
            """\
            ---
            type: singlechoice
            name: S
            choice_layout:
              shuffle: false
            ---

            Which curve? ![The AS curve](img/curve.png)

            ## /choices

            - (x) ![shifted left](img/correct-shift-left.png "left")
            - ( ) <img src="img/shift-right.png" alt="shifted right" title="right">
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    xml = render_xml([Reader(md).read()])
    q = _question(xml)
    curve, left, right = _name(PNG), _name(PNG + b"L"), _name(PNG + b"R")

    qt = q.find("questiontext")
    assert f"![The AS curve](@@PLUGINFILE@@/{curve})" in qt.findtext("text")
    assert _files(qt) == {curve: PNG}

    a, b = q.findall("answer")
    assert a.findtext("text") == f"![Choice image](@@PLUGINFILE@@/{left})"
    assert _files(a) == {left: PNG + b"L"}
    assert b.findtext("text") == f'<img src="@@PLUGINFILE@@/{right}" alt="Choice image">'
    assert _files(b) == {right: PNG + b"R"}
    for leak in ("shift", "left", "right", "img/"):
        assert leak not in "".join(el.findtext("text") for el in (a, b))


def test_metachoice_pool_images_resolve_relative_to_the_file(tmp_path, monkeypatch):
    _png(tmp_path / "m" / "a.png")
    md = tmp_path / "m" / "mc.md"
    md.write_text(
        textwrap.dedent(
            """\
            ---
            type: metachoice
            name: MC
            choices:
              A: "![a](a.png)"
              B: B
            stems:
              S: Pick.
            ---

            ```csv
            choice,S
            A,x
            ```
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    (q,) = Reader(md).read_metachoice().generate_singlechoice(n=2, limit=1, seed=1)
    answers = _question(render_xml([q])).findall("answer")
    assert {n for a in answers for n in _files(a)} == {_name(PNG)}


def test_same_image_twice_is_embedded_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _png(tmp_path / "fig.png")
    q = Q.SingleChoice(name="S", questiontext=Text("![x](fig.png) ![y](./fig.png)", format="markdown"))
    q.set_choice_correct("A").set_choices_wrong("B")
    assert list(_files(_question(render_xml([q])).find("questiontext"))) == [_name(PNG)]


def test_remote_images_and_code_are_left_alone():
    text = "![w](https://example.com/w.png) `![c](c.png)` <img src='@@PLUGINFILE@@/k.png'>"
    q = Q.SingleChoice(name="S", questiontext=Text(text, format="markdown"))
    q.set_choice_correct("A").set_choices_wrong("B")
    qt = _question(render_xml([q])).find("questiontext")
    assert qt.findtext("text") == text
    assert qt.findall("file") == []


@pytest.mark.parametrize(
    "src, message",
    [("fig.svg", "SVG"), ("fig.bmp", "PNG, JPEG, GIF, or WebP"), ("missing.png", "missing.png")],
)
def test_unsupported_or_missing_images_fail(tmp_path, monkeypatch, src, message):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "fig.svg").write_text("<svg/>")
    (tmp_path / "fig.bmp").write_bytes(b"BM")
    q = Q.SingleChoice(name="S", questiontext=f'<img src="{src}">').set_choice_correct("A").set_choices_wrong("B")
    with pytest.raises(ValueError, match=message):
        render_xml([q])


def _order(*texts: str, shuffle: bool) -> list[str]:
    q = Q.MultiChoice(name="M", questiontext="Pick.").set_shuffle(shuffle)
    q.set_choices_correct(texts[0]).set_choices_wrong(*texts[1:])
    return [a.findtext("text") for a in _question(render_xml([q])).findall("answer")]


def test_shuffled_answers_do_not_keep_the_authoring_order():
    # Answer ids follow the XML order and show in image URLs; the correct choice is often first.
    assert _order("A", "B", "C", "D", shuffle=True) == _order("D", "C", "B", "A", shuffle=True)
    assert _order("A", "B", "C", shuffle=False) == ["A", "B", "C"]
