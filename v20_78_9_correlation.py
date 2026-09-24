from typing import List,Dict,Any

def correlation(a:Dict[str,Any],b:Dict[str,Any])->float:
    if a.get('fixture_key')==b.get('fixture_key'): return 1.0
    if a.get('market')==b.get('market') and a.get('selection')==b.get('selection'): return 0.35
    # Explicit evidence is authoritative; otherwise conservative default is 0.
    return abs(float(a.get('correlation',0))) if a.get('correlation') is not None else 0.0

def diversify(candidates:List[Dict[str,Any]], max_corr=0.65, limit=None)->List[Dict[str,Any]]:
    out=[]
    for c in sorted(candidates,key=lambda x:float(x.get('decision_score',x.get('model_probability',0))),reverse=True):
        if any(correlation(c,o)>max_corr for o in out): continue
        out.append(c)
        if limit and len(out)>=limit: break
    return out
