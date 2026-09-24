"""V20.78.6 dynamic evidence weighting and probability calibration.
Weights are derived from evidence availability/quality and optional historical
model performance. Calibration is identity during warm-up and temperature
scaling after enough settled results are supplied. No outcome is fabricated.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List
import math


def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, float(x)))

def prob(v):
    try:
        x=float(v); x=x/100 if 1<x<=100 else x
        return x if 0<=x<=1 else None
    except Exception: return None


def evidence_quality(e: Dict[str,Any]) -> float:
    status=e.get('evidence_status','MISSING')
    status_q={'MISSING':0.30,'SINGLE_SOURCE':0.55,'CONFLICT':0.50,'VERIFIED':0.85}.get(status,0.45)
    keys=('home_xg','away_xg','form_home_prob','home_away_prob','h2h_home_prob',
          'elo_home_prob','lineup_home_prob','injury_home_prob','suspension_home_prob',
          'tactical_home_prob','ml_home_prob')
    present=sum(e.get(k) is not None for k in keys)/len(keys)
    sources=len(e.get('evidence_sources',[]) or [])
    source_q=min(1.0,0.55+0.12*sources)
    return clamp(0.55*status_q+0.25*present+0.20*source_q)


def dynamic_weights(e: Dict[str,Any], model_names: Iterable[str]) -> Dict[str,float]:
    names=list(model_names)
    base={'Poisson':0.24,'Dixon-Coles':0.16,'xG':0.16,'form':0.10,
          'home_away':0.07,'H2H':0.05,'lineup_absence':0.08,'Elo':0.07,
          'ML_context':0.07}
    hist=e.get('model_performance',{}) or {}
    q=evidence_quality(e)
    raw={}
    for name in names:
        b=base.get(name,1.0/max(1,len(names)))
        rec=hist.get(name,{}) if isinstance(hist,dict) else {}
        brier=rec.get('brier') if isinstance(rec,dict) else None
        settled=int(rec.get('settled',0) or 0) if isinstance(rec,dict) else 0
        if brier is not None and settled>0:
            # Lower Brier => larger reliability. Shrink toward neutral until 20 results.
            rel=clamp(1.0-float(brier)/0.30,0.25,1.25)
            shrink=min(1.0,settled/20.0)
            rel=1.0+(rel-1.0)*shrink
        else:
            rel=1.0
        raw[name]=max(1e-9,b*rel)
    # Evidence quality gates the use of context models, while score models remain available.
    for name in ('form','home_away','H2H','lineup_absence','Elo','ML_context'):
        if name in raw: raw[name]*=(0.55+0.45*q)
    s=sum(raw.values()) or 1.0
    return {k:v/s for k,v in raw.items()}


def fit_temperature(results: List[Dict[str,Any]]) -> Dict[str,Any]:
    """Fit a simple binary temperature on settled predictions.
    Each row needs p and y (0/1). Returns identity if fewer than 20 rows.
    """
    rows=[]
    for r in results:
        if str(r.get('result','')).upper() not in ('WIN','LOSS'): continue
        p=prob(r.get('probability')); y=1 if str(r.get('result')).upper()=='WIN' else 0
        if p is not None: rows.append((clamp(p,1e-6,1-1e-6),y))
    n=len(rows)
    if n<20: return {'status':'UNCALIBRATED','valid_results':n,'method':'identity_warmup','temperature':1.0}
    best_t=1.0; best=1e99
    for i in range(25,201):
        t=i/100.0
        loss=0.0
        for p,y in rows:
            z=math.log(p/(1-p))/t
            pc=1/(1+math.exp(-max(-40,min(40,z))))
            loss-=y*math.log(max(1e-12,pc))+(1-y)*math.log(max(1e-12,1-pc))
        if loss<best: best=loss; best_t=t
    return {'status':'CALIBRATED','valid_results':n,'method':'temperature','temperature':best_t}


def apply_temperature(p: float, temperature: float) -> float:
    p=clamp(p,1e-9,1-1e-9)
    t=max(0.05,float(temperature))
    z=math.log(p/(1-p))/t
    return 1/(1+math.exp(-max(-40,min(40,z))))
