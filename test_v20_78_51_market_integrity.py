from v20_78_51_market_registry import lock_candidates,registry
from v20_78_51_market_value import devig,value
from v20_78_51_match_qualification import qualify

def test_source_lock_exact_line():
    vis=[{'market':'O/U','selection':'Over','line':3.5,'odds':1.85}]
    good=lock_candidates([{'market':'O/U','selection':'Over','line':3.5}],vis)[0]
    bad=lock_candidates([{'market':'O/U','selection':'Over','line':2.5}],vis)
    assert good['source_market_locked'] is True
    assert bad == []

def test_devig():
    p=devig([2.0,2.0]); assert abs(sum(p)-1)<1e-9

def test_value():
    x=value(.60,2.0,.50); assert x['fair_odds']==1/0.6 and x['edge']>.09 and x['ev']>.19

def test_qualification():
    x=qualify({'source_market_locked':True,'model_probability':.6,'edge':.1,'ev':.2,'data_confidence':'HIGH'})
    assert x['qualified']
