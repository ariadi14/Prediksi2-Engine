from v20_78_8_market_decision import select_markets
from v20_78_9_correlation import diversify
from v20_78_10_parlay_optimizer import optimize
from v20_78_11_competition_model import competition_profile
from v20_78_12_sensitivity import sensitivity
from v20_78_13_odds_signal import odds_signal
from v20_78_14_backtest import walk_forward
from v20_78_15_learning import update_learning
from v20_78_16_decision_engine import run_prediction

def main():
    p={'calibration':{'uncertainty':{'score':.2},'evidence_quality':.9}}
    vis=[{'fixture_key':'a','market':'O/U','line':2.5,'selection':'Over','odds':1.8,'model_probability':.62}]
    c=select_markets(p,vis); assert c and c[0]['decision']=='PASS'
    assert len(diversify(c))==1
    assert optimize(c,1)['size']==1
    assert competition_profile('Test')['status']=='WARMUP'
    assert sensitivity({'Home':.5,'Draw':.3,'Away':.2},{'lineup':{'Home':.55,'Draw':.28,'Away':.17}})['max_change']>.0
    assert odds_signal([1.9,1.8])['direction']=='SHORTENING'
    assert walk_forward([{'fixture':'a','result':'WIN'}])['lookahead_free']
    assert update_learning([{'result':'WIN'}])['status']=='UNCALIBRATED'
    assert run_prediction([{'fixture_key':'a','prediction':p,'visible_markets':vis}])['fixtures_processed']==1
    print('V20.78.8-16 TEST PASS')
if __name__=='__main__': main()
