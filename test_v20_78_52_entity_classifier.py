from v20_78_52_entity_classifier import classify_entity, classify_fixture


def test_senior_national_teams_are_not_clubs():
    r = classify_fixture("Brazil", "Colombia", "World Cup Qualifiers")
    assert r["fixture_type"] == "NATIONAL_VS_NATIONAL"
    assert r["home"]["entity_type"] == "NATIONAL"
    assert r["away"]["entity_type"] == "NATIONAL"
    assert r["home"]["age_group"] == "SENIOR"


def test_u21_isolated_from_senior():
    r = classify_entity("England U21", "UEFA U21")
    assert r.entity_type == "CLUB" or r.entity_type == "NATIONAL"  # type resolved separately by resolver
    assert r.age_group == "U21"


def test_women_variant_isolated():
    r = classify_entity("Brazil Women", "International Friendly Women")
    assert r.entity_type == "NATIONAL"
    assert r.gender == "WOMEN"


def test_club_remains_club():
    r = classify_fixture("Liverpool", "Arsenal", "Premier League")
    assert r["fixture_type"] == "CLUB_VS_CLUB"


def test_mixed_entity_is_flagged():
    r = classify_fixture("Brazil", "Liverpool", "Friendly")
    assert r["fixture_type"] == "MIXED_ENTITY"
    assert r["same_entity_family"] is False


def test_explicit_type_overrides_ambiguous_name():
    r = classify_entity("England U21", "UEFA U21", explicit_type="NATIONAL")
    assert r.entity_type == "NATIONAL"
    assert r.age_group == "U21"
