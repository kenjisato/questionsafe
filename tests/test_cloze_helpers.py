from questionsafe.questions._cloze_embed import ClozeEmbeddable


def test_prefix_by_fraction_full_credit():
    assert ClozeEmbeddable._prefix_by_fraction(100.0, "X") == "=X"
    # near-100 within tolerance should still be treated as '='
    assert ClozeEmbeddable._prefix_by_fraction(100.0000001, "X") == "=X"


def test_prefix_by_fraction_partial_positive():
    assert ClozeEmbeddable._prefix_by_fraction(50.0, "X") == "%50.0%X"
    assert ClozeEmbeddable._prefix_by_fraction(33.33333, "Y") == "%33.33333%Y"


def test_prefix_by_fraction_zero():
    assert ClozeEmbeddable._prefix_by_fraction(0.0, "X") == "X"


def test_prefix_by_fraction_negative_default_excluded():
    # Negative fractions not included unless include_negative=True
    assert ClozeEmbeddable._prefix_by_fraction(-25.0, "X") == "X"


def test_prefix_by_fraction_negative_included():
    assert ClozeEmbeddable._prefix_by_fraction(-25.0, "Z", include_negative=True) == "%-25.0%Z"


def test_with_feedback_none():
    assert ClozeEmbeddable._with_feedback("tok", None) == "tok"


def test_with_feedback_text():
    assert ClozeEmbeddable._with_feedback("tok", "fb") == "tok#fb"

