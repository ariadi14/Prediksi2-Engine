from v20_78_probability_engine import AdaptiveProbabilityEngine

def test():
    e={
      'home_xg':1.55,'away_xg':1.20,
      'form_home_prob':0.62,'elo_home_prob':0.58,
      'evidence_status':'VERIFIED','evidence_sources':['a','b'],
      'ou_lines':[0.5,1.5,2.5,3.5],
      'handicap_lines':[-1.5,-1.0,-0.5,0.0,0.5,1.0,1.5],
      'ou_probabilities':{'2.5':{'Over':0.64}},
      'hdp_probabilities':{'-0.5':{'Home':0.59}}
    }
    r=AdaptiveProbabilityEngine().predict('TEST',e)
    assert r['status']=='CALCULATED'
    x=r['markets']['1X2']; assert abs(sum(x.values())-1)<1e-9
    assert '2.5' in r['markets']['O/U']
    assert 'Over' in r['markets']['O/U']['2.5']
    assert '-0.5' in r['markets']['HDP']
    assert 0<=r['markets']['O/U']['2.5']['Over']<=1
    assert 0<=r['markets']['HDP']['-0.5']['Home']<=1
    print('V20_78_5_DEDICATED_OU_HDP_TEST_PASS')
if __name__=='__main__': test()
