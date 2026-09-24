from v20_78_35_fixture_validation import validate_fixture
from v20_78_37_probability_activation import ProbabilityActivation
from v20_78_34_provider_connection import ProviderConnection

def test_fixture_validation():
 f={'home':'A','away':'B','competition':'League'}; c={'fixture_id':1,'home_name':'A','away_name':'B','competition':'League','date':'2026-09-23'}
 assert validate_fixture(f,c)['status']=='VALID'
def test_reject_mismatch():
 f={'home':'A','away':'B','competition':'League'}; c={'fixture_id':1,'home_name':'A','away_name':'C','competition':'League'}
 assert validate_fixture(f,c)['status']=='REJECTED'
def test_no_provider_explicit():
 assert ProviderConnection().status()['configured'] is False
def test_probability_blocks_missing():
 r=ProbabilityActivation().run('x',{'status':'MISSING'},[]); assert r['status']=='INSUFFICIENT_DATA'
print('V20.78.38 TEST PASS')
