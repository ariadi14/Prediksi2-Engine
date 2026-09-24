from v20_78_probability_engine import AdaptiveProbabilityEngine

def test():
 e={'home_xg':1.55,'away_xg':1.20,'form_home_prob':.62,'elo_home_prob':.58,
    'evidence_status':'VERIFIED','evidence_sources':['a','b'],
    'ou_lines':[2.5],'handicap_lines':[-.5],
    'model_probabilities':{
      'poisson':{'Home':.43,'Draw':.30,'Away':.27},
      'xg':{'Home':.45,'Draw':.29,'Away':.26},
      'elo':{'Home':.41,'Draw':.31,'Away':.28}},
    'calibration_results':[]}
 r=AdaptiveProbabilityEngine().predict('TEST',e)
 assert r['status']=='CALCULATED'
 assert abs(sum(r['markets']['1X2'].values())-1)<1e-9
 c=r['calibration']['cross_model_consistency']; assert c['models']==4 and c['agreement']>0
 u=r['calibration']['uncertainty']; assert 0<=u['score']<=1 and u['level'] in ('LOW','MEDIUM','HIGH','VERY_HIGH')
 print('V20_78_7_CROSS_MODEL_CONSISTENCY_TEST_PASS')
if __name__=='__main__': test()
