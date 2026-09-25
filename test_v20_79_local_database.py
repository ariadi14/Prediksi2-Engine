from v20_79_local_database import norm

def test_team_normalization():
    assert norm('Skenderbeu') == norm('Skënderbeu')
