from v20_78_probability_engine import AdaptiveProbabilityEngine
from v20_78_51_parlay import optimize

def test_visible_market_pipeline():
    e=AdaptiveProbabilityEngine()
    evidence={'home_xg':1.5,'away_xg':1.0,'evidence_status':'VERIFIED','fixture_resolved':True,'freshness_score':.95,
              'model_1x2':{'Home':.55,'Draw':.25,'Away':.20}}
    pred=e.predict('A|B',evidence)
    rows=e.lock_and_value_visible_markets(pred,[{'market':'1X2','selection':'Home','line':None,'odds':2.0}, {'market':'O/U','selection':'Over','line':3.5,'odds':1.9}])
    assert len(rows)==2
    assert all(r['source_market_locked'] for r in rows)

def test_no_forced_quota():
    r=optimize([{'fixture_key':'A','qualified':True,'model_probability':.8,'odds':1.8}],size=7)
    assert r['size']==1 and r['quota_requested']==7
