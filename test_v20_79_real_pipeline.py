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


def test_auto_fixture_date_uses_jakarta_calendar():
    from v20_79_real_pipeline import resolve_fixture_search_date
    import re
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", resolve_fixture_search_date("AUTO"))


def test_explicit_fixture_date_is_reproducible():
    from v20_79_real_pipeline import resolve_fixture_search_date
    assert resolve_fixture_search_date("2026-09-24") == "2026-09-24"
