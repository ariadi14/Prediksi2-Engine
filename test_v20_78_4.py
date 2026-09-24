from v20_78_probability_engine import score_matrix, markets_from_matrix
from v20_78_4_ensemble import EvidenceWeightedEnsemble

def test_matrix_and_ensemble():
    m=score_matrix(1.55,1.15)
    base=markets_from_matrix(m)['1X2']
    e={'form_home_prob':.60,'elo_home_prob':.58,'evidence_sources':['A','B'],'evidence_status':'VERIFIED','home_xg':1.55,'away_xg':1.15}
    out,meta=EvidenceWeightedEnsemble().blend_1x2(base,e)
    assert abs(sum(out)-1)<1e-9
    assert meta['components']

def test_explicit_model():
    m=score_matrix(1.4,1.1); base=markets_from_matrix(m)['1X2']
    e={'model_1x2':{'Home':70,'Draw':20,'Away':10},'explicit_context_weight':.5}
    out,_=EvidenceWeightedEnsemble().blend_1x2(base,e)
    assert abs(sum(out)-1)<1e-9
    assert out[0] > base['Home']

def test_confidence():
    c=EvidenceWeightedEnsemble().market_confidence(.68,{'evidence_sources':['A','B'],'evidence_status':'VERIFIED','home_xg':1,'away_xg':1,'form_home_prob':.6,'elo_home_prob':.6,'h2h_home_prob':.55,'lineup_home_prob':.6})
    assert 0<=c<=100

if __name__=='__main__':
    test_matrix_and_ensemble(); test_explicit_model(); test_confidence(); print('V20.78.4 TEST PASS')
