from v20_78_52_provider_router import route_provider


def test_national_fixture_uses_broad_provider():
    r = route_provider("World Cup Qualifiers", home="Brazil", away="Colombia")
    assert r.fixture_type == "NATIONAL_VS_NATIONAL"
    assert r.primary == "api-football"
    assert "openfoot" not in [r.primary, *r.fallback]
    assert "sportmonks" not in [r.primary, *r.fallback]


def test_csv_is_fallback_when_api_football_unavailable():
    r = route_provider("Danish Superliga", home="Team A", away="Team B", api_football_available=False)
    assert r.primary == "football-data-csv"
    assert r.fallback == []


def test_other_club_competition_uses_api_football_first():
    r = route_provider("Premier League", home="Liverpool", away="Arsenal")
    assert r.primary == "api-football"
    assert "sportmonks" not in [r.primary, *r.fallback]


def test_missing_provider_does_not_create_fake_route():
    r = route_provider("World Cup", home="Brazil", away="Colombia", api_football_available=False, football_data_available=False, sportmonks_available=False)
    assert r.primary == "missing"
    assert r.fallback == []


def test_api_football_is_first_and_csv_is_fallback():
    import os
    from v20_78_34_provider_connection import ProviderConnection
    os.environ["API_FOOTBALL_KEY"]="test-key"
    os.environ["FOOTBALL_DATA_CSV_PATH"]="/tmp/nonexistent-prediksi2.csv"
    conn=ProviderConnection()
    assert [p.name for p in conn.providers] == ["api-football", "football-data-csv", "football-local-db"]
    assert all(p.name != "openfoot" for p in conn.providers)
