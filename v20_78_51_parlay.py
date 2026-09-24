"""Correlation-aware parlay selection. Never fills a requested quota with weak legs."""
from __future__ import annotations
import math
from typing import Any, Dict, List

def _corr(a,b):
    try:
        x=str(a.get('fixture_key','')); y=str(b.get('fixture_key',''))
        if x and x==y:return 1.0
        # Same match is the principal hard correlation guard; explicit source correlation may be supplied.
        return float(a.get('correlation_with',{}).get(y,0))
    except Exception:return 0.0

def optimize(candidates: List[Dict[str,Any]], size=7, max_corr=0.65):
    pool=[]
    for c in candidates:
        if not c.get('qualified'):continue
        try:p=float(c['model_probability']); o=float(c['odds'])
        except (KeyError,TypeError,ValueError):continue
        if not (0<p<1 and o>1):continue
        ev=p*o-1
        score=math.log(p)+0.20*max(-1,min(1,ev))
        pool.append((score,c))
    pool.sort(key=lambda z:z[0],reverse=True)
    chosen=[]
    for _,c in pool:
        if any(_corr(c,x)>max_corr for x in chosen):continue
        chosen.append(c)
        if len(chosen)>=size:break
    joint=math.prod(float(x['model_probability']) for x in chosen) if chosen else 0.0
    odds=math.prod(float(x['odds']) for x in chosen) if chosen else 1.0
    return {'status':'PASS' if chosen else 'NO_BET','legs':chosen,'size':len(chosen),'joint_probability':joint,'total_odds':odds,'quota_requested':size,'quota_filled':len(chosen)}
