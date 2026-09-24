"""Market-specific calibration and reliability metrics for V20.78.51."""
from __future__ import annotations
import math
from typing import Any, Dict, Iterable, List, Sequence, Tuple

def brier(pairs): return sum((float(p)-float(y))**2 for p,y in pairs)/len(pairs) if pairs else None

def log_loss(pairs):
    if not pairs:return None
    s=0
    for p,y in pairs:
        p=min(.999999,max(.000001,float(p))); y=int(y)
        s += -(y*math.log(p)+(1-y)*math.log(1-p))
    return s/len(pairs)

def ece(pairs,bins=10):
    if not pairs:return None
    total=len(pairs); score=0
    for i in range(bins):
        lo=i/bins; hi=(i+1)/bins
        bucket=[(float(p),int(y)) for p,y in pairs if (lo<=p<hi) or (i==bins-1 and lo<=p<=hi)]
        if bucket:
            acc=sum(y for _,y in bucket)/len(bucket); conf=sum(p for p,_ in bucket)/len(bucket)
            score += len(bucket)/total*abs(acc-conf)
    return score

def binary_temperature_fit(pairs):
    if len(pairs)<30:return {'status':'UNCALIBRATED','method':'none','samples':len(pairs)}
    best=(1.0, float('inf'))
    for t in [0.70,0.80,0.90,1.0,1.10,1.20,1.35,1.50,1.75,2.0]:
        transformed=[]
        for p,y in pairs:
            p=min(.999999,max(.000001,float(p))); z=math.log(p/(1-p))/t; q=1/(1+math.exp(-z)); transformed.append((q,y))
        ll=log_loss(transformed)
        if ll is not None and ll<best[1]:best=(t,ll)
    return {'status':'CALIBRATED','method':'temperature','temperature':best[0],'log_loss':best[1],'samples':len(pairs)}

def summarize_market(results: Sequence[Dict[str,Any]], market: str) -> Dict[str,Any]:
    pairs=[]
    for r in results:
        if str(r.get('market','')).upper()==market.upper() and r.get('probability') is not None and r.get('actual') is not None:
            pairs.append((r['probability'],r['actual']))
    return {'market':market,'samples':len(pairs),'brier':brier(pairs),'log_loss':log_loss(pairs),'ece':ece(pairs),'calibration':binary_temperature_fit(pairs)}
