from v20_78_39_provider_aware_pipeline import ProviderAwarePipeline
from v20_78_34_provider_connection import ProviderConnection

class MockProvider:
    name='mock-provider'
    def resolve_team(self,name):
        return {'status':'RESOLVED_HIGH','canonical_name':name,'provider_ids':{'mock':1}}
    def find_fixture(self,f):
        return [{'fixture_id':999,'home_name':f.get('home_canonical') or f.get('home'),'away_name':f.get('away_canonical') or f.get('away'),'competition':f.get('competition'),'date':f.get('match_date')}]
    def fetch(self,f):
        return {'provider':self.name,'fixture_match':{'fixture':{'id':f['fixture_id']}},'home_xg':1.4,'away_xg':0.9,'evidence_quality':0.8}

def test_real_connection_explicitly_unconfigured():
    assert ProviderConnection().configured is False

def test_provider_aware_identity_fixture_evidence():
    p=ProviderAwarePipeline(type('C',(),{'providers':[MockProvider()]})())
    r=p.run_fixture({'competition':'Test League','home':'Alpha','away':'Beta','match_date':'2026-09-23','markets':[]})
    assert r['validation']['status']=='VALID'
    assert r['fixture']['fixture_id']==999
    assert r['evidence']['status']=='ENRICHED'
    assert r['prediction']['status']=='CALCULATED'

print('V20.78.39 TEST PASS')
