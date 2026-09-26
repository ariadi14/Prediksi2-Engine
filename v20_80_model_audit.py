"""V20.80 external-model audit and adaptive ensemble utilities.

Real external probabilities may be supplied through evidence["external_model_probabilities"].
No external model is trusted merely because it exists; it must have audited settled results.
"""
from __future__ import annotations
import math
from typing import Any, Dict, Iterable, List, Optional

ORDER=("Home","Draw","Away")


def _norm3(p: Dict[str, Any]) -> Optional[Dict[str, float]]:
    try:
        x={k:float(p[k]) for k in ORDER}
    except (KeyError,TypeError,ValueError):
        return None
    if any(v<0 for v in x.values()): return None
    s=sum(x.values())
    return {k:v/s for k,v in x.items()} if s>0 else None


def brier_1x2(rows: Iterable[Dict[str, Any]]) -> Optional[float]:
    vals=[]
    for r in rows:
        p=_norm3(r.get("probabilities",{})); y=str(r.get("result","")).upper()
        if not p or y not in ("HOME","DRAW","AWAY"): continue
        vals.append(sum((p[k]-(1.0 if k.upper()==y else 0.0))**2 for k in ORDER))
    return sum(vals)/len(vals) if vals else None


def log_loss_1x2(rows: Iterable[Dict[str, Any]]) -> Optional[float]:
    vals=[]
    for r in rows:
        p=_norm3(r.get("probabilities",{})); y=str(r.get("result","")).upper()
        if not p or y not in ("HOME","DRAW","AWAY"): continue
        vals.append(-math.log(max(1e-12,p[y.title()])))
    return sum(vals)/len(vals) if vals else None


def rps_1x2(rows: Iterable[Dict[str, Any]]) -> Optional[float]:
    vals=[]
    for r in rows:
        p=_norm3(r.get("probabilities",{})); y=str(r.get("result","")).upper()
        if not p or y not in ("HOME","DRAW","AWAY"): continue
        cp=cy=score=0.0
        for k in ORDER[:-1]:
            cp+=p[k]
            if k.upper()==y: cy=1.0
            score+=(cp-cy)**2
        vals.append(score/2.0)
    return sum(vals)/len(vals) if vals else None


def calibration_ece(rows: Iterable[Dict[str, Any]], bins: int=10) -> Optional[float]:
    buckets=[[] for _ in range(bins)]
    for r in rows:
        p=_norm3(r.get("probabilities",{})); y=str(r.get("result","")).upper()
        if not p or y not in ("HOME","DRAW","AWAY"): continue
        for k in ORDER:
            buckets[min(bins-1,int(p[k]*bins))].append((p[k],1.0 if k.upper()==y else 0.0))
    total=sum(len(b) for b in buckets)
    if not total: return None
    return sum(len(b)/total*abs(sum(x for x,_ in b)/len(b)-sum(y for _,y in b)/len(b)) for b in buckets if b)


def audit_model(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n=sum(1 for r in rows if _norm3(r.get("probabilities",{})) and str(r.get("result","")).upper() in ("HOME","DRAW","AWAY"))
    return {"settled":n,"brier":brier_1x2(rows),"log_loss":log_loss_1x2(rows),"rps":rps_1x2(rows),"ece":calibration_ece(rows)}


def adaptive_weights(model_metrics: Dict[str, Dict[str, Any]], minimum_settled: int=20) -> Dict[str,float]:
    raw={}
    for name,m in (model_metrics or {}).items():
        n=int(m.get("settled",0) or 0)
        if n<minimum_settled:
            raw[name]=1.0
            continue
        score=0.5
        if m.get("brier") is not None:
            score+=max(-0.4,min(0.4,(0.667-float(m["brier"]))/0.667))
        if m.get("log_loss") is not None:
            score+=max(-0.4,min(0.4,(1.099-float(m["log_loss"]))/1.099))
        raw[name]=max(0.10,score)
    s=sum(raw.values()) or 1.0
    return {k:v/s for k,v in raw.items()}


def external_model_probabilities(evidence: Dict[str, Any]) -> Dict[str, Dict[str,float]]:
    raw=evidence.get("external_model_probabilities",{})
    out={}
    if isinstance(raw,dict):
        for name,p in raw.items():
            q=_norm3(p if isinstance(p,dict) else {})
            if q: out[str(name)]=q
    return out


def ensemble_1x2(base: Dict[str,float], external: Dict[str,Dict[str,float]],
                  weights: Dict[str,float]) -> Dict[str,Any]:
    models={"v20_79_baseline":_norm3(base)}
    models.update(external or {})
    active=[(n,p,float(weights.get(n,1.0))) for n,p in models.items() if p]
    if not active: return {"probabilities":base,"weights":{},"status":"BASELINE_ONLY"}
    den=sum(max(0,w) for _,_,w in active) or 1.0
    out={k:0.0 for k in ORDER}; used={}
    for n,p,w in active:
        ww=max(0,w)/den; used[n]=ww
        for k in ORDER: out[k]+=ww*p[k]
    return {"probabilities":_norm3(out),"weights":used,"status":"ADAPTIVE_ENSEMBLE" if len(active)>1 else "BASELINE_ONLY"}
