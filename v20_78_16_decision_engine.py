from typing import Dict,Any,List
from v20_78_8_market_decision import select_markets
from v20_78_9_correlation import diversify
from v20_78_10_parlay_optimizer import optimize
from v20_78_15_learning import update_learning

VERSION='V20.78.16'

def run_prediction(fixtures:List[Dict[str,Any]], parlay_size=7)->Dict[str,Any]:
    results=[]; candidates=[]
    for f in fixtures:
        pred=f.get('prediction',{}); visible=f.get('visible_markets',[])
        selected=select_markets(pred,visible)
        results.append({'fixture_key':f.get('fixture_key'),'prediction':pred,'market_candidates':selected})
        candidates.extend(selected)
    diverse=diversify(candidates)
    parlay=optimize(diverse,size=parlay_size)
    return {'version':VERSION,'fixtures_processed':len(fixtures),'results':results,'candidate_count':len(candidates),'diversified_count':len(diverse),'parlay':parlay}

def learn(records:List[Dict[str,Any]])->Dict[str,Any]: return update_learning(records)
