import pytest

from questionsafe import Q


def test_singlechoice_add_choice_correct_guard_raises_when_correct_exists():
    sc = Q.SingleChoice(name="SC/guard").ask("Pick one")
    sc.set_choice_correct("A")
    # Adding a second correct via colorful API should be guarded
    with pytest.raises(ValueError):
        sc.add_choice_correct("B")
    # Still valid single correct
    sc.validate()
