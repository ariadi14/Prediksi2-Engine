"""V20.78.7 cross-model consistency and uncertainty diagnostics."""
from __future__ import annotations
from typing import Dict, Any, Iterable
import math

def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, float(x)))

def entropy(probs: Iterable[float]) -> float:
    ps=[max(1e-12,float(p)) for p in probs]
    s=sum(ps) or 1.0
    ps=[p/s for p in ps]
    h=-sum(p*math.log(p) for p in ps)
    return h/max(1e-12,math.log(len(ps))) if len(ps)>1 else 0.0

def consistency_1x2(model_probs: Dict[str, Dict[str,float]]) -> Dict[str,Any]:
    rows=[]
    for name,p in model_probs.items():
        if all(k in p for k in ('Home','Draw','Away')):
            rows.append((name,{k:float(p[k]) for k in ('Home','Draw','Away')}))
    if not rows:
        return {'status':'NO_MODEL_COMPARISON','agreement':None,'dispersion':None,'models':0}
    means={k:sum(p[k] for _,p in rows)/len(rows) for k in ('Home','Draw','Away')}
    variance=sum(sum((p[k]-means[k])**2 for k in means) for _,p in rows)/(len(rows)*3)
    dispersion=math.sqrt(variance)
    # 1 when identical, 0 when model distributions are very dispersed.
    agreement=clamp(1.0-dispersion/0.25)
    return {'status':'OK','agreement':round(agreement,6),'dispersion':round(dispersion,6),'models':len(rows),'mean':means}

def uncertainty(final_1x2: Dict[str,float], agreement: float|None, evidence_quality: float=0.5) -> Dict[str,Any]:
    h=entropy(final_1x2.values())
    a=0.5 if agreement is None else clamp(agreement)
    q=clamp(evidence_quality)
    # Higher entropy, lower agreement, and weaker evidence mean greater uncertainty.
    u=clamp(0.50*h + 0.30*(1-a) + 0.20*(1-q))
    if u < .25: level='LOW'
    elif u < .50: level='MEDIUM'
    elif u < .75: level='HIGH'
    else: level='VERY_HIGH'
    return {'score':round(u,6),'level':level,'entropy':round(h,6),'agreement':round(a,6),'evidence_quality':round(q,6)}
