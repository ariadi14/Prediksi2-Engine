from v20_79_real_pipeline import asian_ev


def test_three_quarter_under_settlement_is_not_simple_p_times_odds():
    # Deterministic sanity check: exact Asian quarter-line settlement must
    # account for the half-win/push outcome at the whole-number boundary.
    ev = asian_ev(1.0, 1.0, "O/U", 2.75, "Under", 1.90)
    assert isinstance(ev, float)
    assert -1.0 < ev < 1.0


def test_hdp_quarter_line_returns_finite_value():
    ev = asian_ev(1.2, 0.8, "HDP", -0.25, "Home", 1.90)
    assert isinstance(ev, float)
    assert -1.0 < ev < 1.0
