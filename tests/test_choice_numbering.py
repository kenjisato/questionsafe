"""Choice numbering: `numbering` replaces `labels`; Moodle's full-form keys are read (#11)."""
from __future__ import annotations

import textwrap
import warnings

import pytest
from lxml import etree

from questionsafe import Q, Reader, render_xml


def _xml_numbering(q) -> str:
    return etree.fromstring(render_xml([q])).findtext("question[@type='multichoice']/answernumbering")


def _mc():
    return Q.MultiChoice(name="M", questiontext="Pick.").set_choices_correct("A").set_choices_wrong("B")


def _read(tmp_path, front: str):
    p = tmp_path / "q.md"
    p.write_text(f"---\n{textwrap.dedent(front).strip()}\n---\n\nPick.\n", encoding="utf-8")
    return Reader(p).read()


# --- Python API ---


def test_numbering_defaults_to_moodles_default():
    # Moodle's qtype_multichoice/answernumbering setting and XML importer both default to abc.
    assert Q.MultiChoice().numbering == "abc"
    assert Q.SingleChoice().numbering == "abc"
    assert _xml_numbering(_mc()) == "abc"


def test_set_numbering_and_choice_layout():
    assert _xml_numbering(_mc().set_numbering("123")) == "123"
    assert _xml_numbering(_mc().set_choice_layout(numbering="iii")) == "iii"


def test_labels_api_is_deprecated_but_still_works():
    q = _mc()
    with pytest.warns(DeprecationWarning, match="set_numbering"):
        q.set_labels("ABCD")
    assert q.numbering == "ABCD"
    with pytest.warns(DeprecationWarning, match="numbering="):
        q.set_choice_layout(labels="123")
    assert q.numbering == "123"
    with pytest.warns(DeprecationWarning, match="numbering"):
        q.labels = "III"
    with pytest.warns(DeprecationWarning, match="numbering"):
        assert q.labels == "III"


def test_choice_layout_rejects_labels_with_numbering():
    with pytest.raises(TypeError, match="numbering"), warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        _mc().set_choice_layout(labels="abc", numbering="123")


# --- Markdown reader ---


@pytest.mark.parametrize("qtype", ["singlechoice", "multichoice"])
def test_reader_choice_layout_numbering(tmp_path, qtype):
    q = _read(
        tmp_path,
        f"""
        type: {qtype}
        name: Q
        choices: {{correct: [A], wrong: [B]}}
        choice_layout: {{numbering: "123", shuffle: false}}
        """,
    )
    assert (q.numbering, q.shuffle) == ("123", False)


def test_reader_choice_layout_labels_is_deprecated(tmp_path):
    # Markdown authors are end users of the library: FutureWarning is shown by default.
    with pytest.warns(FutureWarning, match="numbering"):
        q = _read(
            tmp_path,
            """
            type: multichoice
            name: Q
            choices: {correct: [A], wrong: [B]}
            choice_layout: {labels: ABCD}
            """,
        )
    assert q.numbering == "ABCD"


def test_reader_full_form_moodle_keys(tmp_path):
    q = _read(
        tmp_path,
        """
        type: multichoice
        name: Q
        answers:
          - {text: A, fraction: 100}
          - {text: B, fraction: 50}
          - {text: C, fraction: 0}
        single: true
        answernumbering: ABCD
        shuffleanswers: false
        """,
    )
    assert (q.single_choice, q.numbering, q.shuffle) == (True, "ABCD", False)
    q.validate()


def test_reader_full_form_shuffleanswers_on_singlechoice(tmp_path):
    q = _read(
        tmp_path,
        """
        type: singlechoice
        name: Q
        choices: {correct: [A], wrong: [B]}
        answernumbering: none
        shuffleanswers: 0
        """,
    )
    assert (q.numbering, q.shuffle) == ("none", False)


@pytest.mark.parametrize(
    "keys",
    [
        "answernumbering: abc\nchoice_layout: {numbering: abc}",
        "shuffleanswers: true\nchoice_layout: {shuffle: true}",
        "single: true\nchoice_layout: {single_choice: true}",
        "choice_layout: {numbering: abc, labels: abc}",
    ],
)
def test_reader_rejects_both_forms(tmp_path, keys):
    with pytest.raises(ValueError, match="not both"), warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        _read(tmp_path, f"type: multichoice\nname: Q\nchoices: {{correct: [A], wrong: [B]}}\n{keys}")
