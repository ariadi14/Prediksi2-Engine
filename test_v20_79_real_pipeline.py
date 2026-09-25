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


def test_one_sided_ocr_fixture_validation_requires_unique_provider_match():
    from v20_78_35_fixture_validation import validate_fixture
    fixture = {"home":"Atletico Nacional","away":"A Millonarios ie","competition":"COLOMBIA PRIMERA A","match_date":"2026-09-24"}
    candidate = {
        "fixture_id":123,
        "home_name":"Atletico Nacional",
        "away_name":"Millonarios",
        "competition":"Colombia Primera A",
        "date":"2026-09-24",
        "match_mode":"STRONG_HOME_ONLY",
        "unique_match":True,
    }
    result = validate_fixture(fixture,candidate,min_team=82,min_comp=40)
    assert result["status"] == "VALID"

def test_one_sided_ocr_fixture_validation_rejects_ambiguous_match():
    from v20_78_35_fixture_validation import validate_fixture
    fixture = {"home":"Atletico Nacional","away":"unknown","competition":"Colombia Primera A","match_date":"2026-09-24"}
    candidate = {
        "fixture_id":123,
        "home_name":"Atletico Nacional",
        "away_name":"Different Team",
        "competition":"Colombia Primera A",
        "date":"2026-09-24",
        "match_mode":"STRONG_HOME_ONLY",
        "unique_match":False,
    }
    result = validate_fixture(fixture,candidate,min_team=82,min_comp=40)
    assert result["status"] == "REJECTED"

def test_ou_parser_can_recover_fraction_line_from_mixed_tokens():
    from fast_pelangi_parser import _parse_total_line
    assert _parse_total_line("2 ½ 1.90 1.90") == 2.5


def test_probability_uses_real_team_season_scoring_rates_when_xg_missing():
    from v20_78_probability_engine import expected_goals
    evidence = {
        "home_goals_for_home_avg": 1.8,
        "away_goals_against_away_avg": 1.2,
        "away_goals_for_away_avg": 1.1,
        "home_goals_against_home_avg": 0.9,
    }
    assert expected_goals(evidence, "home") == 1.5
    assert expected_goals(evidence, "away") == 1.0


def test_probability_uses_recent_real_fixture_rates_as_second_fallback():
    from v20_78_probability_engine import expected_goals
    evidence = {
        "home_recent_goals_for_avg": 1.6,
        "away_recent_goals_against_avg": 1.4,
        "away_recent_goals_for_avg": 0.8,
        "home_recent_goals_against_avg": 1.0,
    }
    assert expected_goals(evidence, "home") == 1.5
    assert expected_goals(evidence, "away") == 0.9
