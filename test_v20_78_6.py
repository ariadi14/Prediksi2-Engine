from v20_78_probability_engine import AdaptiveProbabilityEngine
from v20_78_6_adaptive_weights import dynamic_weights, fit_temperature

def test():
 e={'home_xg':1.55,'away_xg':1.20,'form_home_prob':.62,'elo_home_prob':.58,
    'evidence_status':'VERIFIED','evidence_sources':['a','b'],
    'ou_lines':[2.5],'handicap_lines':[-.5],
    'calibration_results':[{'probability':.6,'result':'WIN'}]*20}
 r=AdaptiveProbabilityEngine().predict('TEST',e)
 assert r['status']=='CALCULATED'
 assert abs(sum(r['markets']['1X2'].values())-1)<1e-9
 w=r['model_components']['dynamic_weights']; assert abs(sum(w.values())-1)<1e-9
 assert r['calibration']['status']=='CALIBRATED'
 print('V20_78_6_DYNAMIC_WEIGHT_CALIBRATION_TEST_PASS')
if __name__=='__main__': test()
