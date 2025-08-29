from questionsafe.quiz import Quiz


def test_add_category_inherits_parent_category_when_set() -> None:
    quiz = Quiz(category="Course/Week1")
    quiz.add_category("Intro")
    xml = quiz.to_xml().decode("utf-8")
    assert '<question type="category">' in xml
    assert "<category><text>$course$/Course/Week1/Intro</text></category>" in xml


def test_add_category_without_inherit_uses_path_as_is() -> None:
    quiz = Quiz(category="Course/Week1")
    quiz.add_category("Intro-Absolute", inherit=False)
    xml = quiz.to_xml().decode("utf-8")
    assert "<category><text>$course$/Intro-Absolute</text></category>" in xml
