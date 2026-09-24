from v20_78_52_entity_classifier import classify_fixture
from v20_78_52_competition_resolver import resolve_competition
from v20_78_52_provider_router import route_provider
from v20_78_52_data_quality_bridge import build_quality_bridge

def test_national_entity():
    x=classify_fixture("Brazil","Colombia","World Cup Qualifier")
    assert x["fixture_type"]=="NATIONAL_VS_NATIONAL"

def test_women_does_not_use_single_letter_w_marker():
    x=classify_fixture("Liverpool","Arsenal","Premier League")
    assert x["fixture_type"]=="CLUB_VS_CLUB"

def test_u21():
    x=classify_fixture("England U21","Germany U21","UEFA U21 Championship")
    assert x["home"]["age_group"]=="U21"

def test_generic_superliga_is_not_sportmonks():
    r=route_provider("Superliga",home="Brazil",away="Colombia")
    assert r.primary=="api-football"

def test_danish_superliga_routes_sportmonks():
    r=route_provider("Danish Superliga",home="FC Copenhagen",away="Brondby")
    assert r.primary=="sportmonks"

def test_competition_id_increases_confidence():
    assert resolve_competition("League",competition_id=123).confidence=="HIGH"

def test_quality_bridge():
    q=build_quality_bridge({"acquisition_meta":{"fixture":{"status":"LIVE","source":"api-football"},"xg":{"status":"MISSING","source":None}}})
    assert q["status"]=="PARTIAL" and q["counts"]["missing"]==1 and q["no_data_is_not_negative"]
