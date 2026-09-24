"""Market value math: de-vig, fair odds, edge and EV.
Works per market group so overround is removed from the visible source prices.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List

def implied(odds):
    try:
        o=float(odds); return 1/o if o>1 else None
    except (TypeError,ValueError): return None

def devig(odds: Iterable[Any]) -> List[float]:
    raw=[implied(o) for o in odds]; valid=[x for x in raw if x is not None]
    s=sum(valid)
    if not valid or s<=0: return [None if x is None else x/s for x in raw]
    return [None if x is None else x/s for x in raw]

def fair_odds(p):
    try:
        p=float(p); return 1/p if p>0 else None
    except (TypeError,ValueError): return None

def value(model_p, odds, market_fair_p=None):
    try:
        p=float(model_p); o=float(odds)
    except (TypeError,ValueError): return {}
    ip=implied(o); fair=fair_odds(p)
    edge=p-(market_fair_p if market_fair_p is not None else ip) if ip is not None else None
    ev=p*o-1 if o>1 else None
    return {'model_probability':p,'implied_probability':ip,'market_fair_probability':market_fair_p,
            'fair_odds':fair,'edge':edge,'ev':ev}

def enrich_group(rows: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    probs=devig([r.get('odds') for r in rows])
    out=[]
    for r,mp in zip(rows,probs):
        x=dict(r); x.update(value(r.get('model_probability'),r.get('odds'),mp)); out.append(x)
    return out
