from questionsafe import Q, Text


def test_set_hints_auto_penalty_common_sequences():
    # 0 hints -> penalty ~ 1.0 -> snaps to 1.0
    mc0 = Q.MultiChoice(name="mc0", questiontext=Text("<p>q</p>")).set_hints()
    assert abs(mc0.penalty - 1.0) <= 1e-6

    # 1 hint -> 0.5
    mc1 = Q.MultiChoice(name="mc1", questiontext=Text("<p>q</p>")).set_hints("h1")
    assert abs(mc1.penalty - 0.5) <= 1e-6

    # 2 hints -> ~0.3333333 (nearest allowed)
    mc2 = Q.MultiChoice(name="mc2", questiontext=Text("<p>q</p>")).set_hints("h1", "h2")
    assert abs(mc2.penalty - 0.3333333) <= 1e-6

    # 3 hints -> 0.25
    mc3 = Q.MultiChoice(name="mc3", questiontext=Text("<p>q</p>")).set_hints(
        "h1", "h2", "h3"
    )
    assert abs(mc3.penalty - 0.25) <= 1e-6

    # 4 hints -> 1/5=0.2 -> 0.2
    mc4 = Q.MultiChoice(name="mc4", questiontext=Text("<p>q</p>")).set_hints(
        "h1", "h2", "h3", "h4"
    )
    assert abs(mc4.penalty - 0.2) <= 1e-6


def test_set_hints_penalty_override_and_none():
    mc = Q.MultiChoice(name="mc", questiontext=Text("<p>q</p>"))
    # Explicit override to 0.1
    mc.set_hints("a", penalty=0.1)
    assert abs(mc.penalty - 0.1) <= 1e-6

    # penalty=None should not change current penalty when changing hints
    before = mc.penalty
    mc.set_hints("a", "b", penalty=None)
    assert abs(mc.penalty - before) <= 1e-6
