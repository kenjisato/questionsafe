from __future__ import annotations

import pytest


def _tf(name: str = "TF"):
    from questionsafe import Q

    return Q.TrueFalse(name).ask("Really?").set_correct_if_true()


def test_parse_version_accepts_major_minor():
    from questionsafe.writer.moodle import parse_version

    assert parse_version("4.5") == (4, 5)
    assert parse_version("3.11") == (3, 11)


@pytest.mark.parametrize("bad", ["", "4", "x.y", "4.5.1", "v4.5"])
def test_parse_version_rejects_other_forms(bad: str):
    from questionsafe.writer.moodle import parse_version

    with pytest.raises(ValueError):
        parse_version(bad)


def test_check_target_flags_idnumber_before_moodle_36():
    from questionsafe.writer.moodle import check_target

    q = _tf().set_idnumber("q-001")
    msgs = check_target([q], "3.5")
    assert len(msgs) == 1
    assert "idnumber" in msgs[0]
    assert "3.6" in msgs[0]


def test_check_target_passes_idnumber_from_moodle_36():
    from questionsafe.writer.moodle import check_target

    q = _tf().set_idnumber("q-001")
    assert check_target([q], "3.6") == []
    assert check_target([q], "4.5") == []


def test_check_target_passes_without_idnumber():
    from questionsafe.writer.moodle import check_target

    assert check_target([_tf()], "3.5") == []


def test_check_target_accepts_quiz_and_skips_category():
    from questionsafe import Q, Quiz
    from questionsafe.writer.moodle import check_target

    quiz = Quiz().add(Q.Category("Top"), _tf().set_idnumber("q-001"))
    msgs = check_target(quiz, "3.5")
    assert len(msgs) == 1
