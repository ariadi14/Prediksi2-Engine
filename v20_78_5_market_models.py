"""V20.78.5 Dedicated O/U and HDP market models.
Derives market probabilities directly from score matrix and contextual goal-rate evidence.
No forced market; only requested/visible lines are returned.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, Optional
import math


def clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, float(x)))

def prob(v):
    try:
        x=float(v); x=x/100 if 1<x<=100 else x
        return x if 0<=x<=1 else None
    except Exception: return None


def weighted_probability(values):
    pairs=[]
    for v,w in values:
        p=prob(v)
        if p is not None and w>0: pairs.append((p,float(w)))
    if not pairs: return None
    return sum(p*w for p,w in pairs)/sum(w for _,w in pairs)


def ou_from_matrix(matrix, line):
    over=under=push=0.0
    for h,row in enumerate(matrix):
        for a,p in enumerate(row):
            total=h+a
            if total>line: over+=p
            elif total<line: under+=p
            else: push+=p
    # For integer lines, return win probabilities plus push separately.
    if abs(line-round(line))<1e-9:
        denom=max(1e-12,over+under)
        return {'Over':over/denom,'Under':under/denom,'Push':push}
    return {'Over':over,'Under':under,'Push':0.0}


def asian_hdp_from_matrix(matrix, line):
    """Home/Away probabilities for Asian handicap, including quarter-line splits.
    Returns win, lose and push/half-push information per side.
    """
    # For quarter lines, split into the adjacent half-lines and average settlement.
    # Quarter lines (.25/.75 etc.) are the average of adjacent half-lines.
    if abs(line*4-round(line*4))<1e-9 and abs(line*2-round(line*2))>1e-9:
        lo=math.floor(line*2)/2
        hi=math.ceil(line*2)/2
        a=asian_hdp_from_matrix(matrix,lo)
        b=asian_hdp_from_matrix(matrix,hi)
        return {k:(a[k]+b[k])/2 for k in a}
    home_win=away_win=home_push=away_push=0.0
    for h,row in enumerate(matrix):
        for a,p in enumerate(row):
            d=(h-a)+line
            if d>1e-12: home_win+=p
            elif d<-1e-12: away_win+=p
            else: home_push+=p; away_push+=p
    return {'Home':home_win,'Away':away_win,'HomePush':home_push,'AwayPush':away_push}


def dedicated_ou(evidence: Dict[str,Any], matrix, lines: Iterable[float]):
    """Blend matrix O/U with independent total-goal evidence when available."""
    out={}
    total_xg=None
    hx=evidence.get('home_xg'); ax=evidence.get('away_xg')
    if hx is not None and ax is not None:
        try: total_xg=float(hx)+float(ax)
        except Exception: pass
    # Optional provider total-goal probabilities can be supplied per line.
    provider=evidence.get('ou_probabilities',{})
    for line in lines:
        key=str(line); m=ou_from_matrix(matrix,float(line))
        over=m['Over']; components=[('score_matrix',over,0.70)]
        if isinstance(provider,dict):
            item=provider.get(key)
            if isinstance(item,dict) and item.get('Over') is not None:
                components.append(('provider',item['Over'],0.30))
        p=weighted_probability([(v,w) for _,v,w in components])
        p=clamp(p if p is not None else over)
        out[key]={'Over':p,'Under':1-p,'Push':m.get('Push',0.0),
                  'components':[name for name,_,_ in components],
                  'total_xg':total_xg}
    return out


def dedicated_hdp(evidence: Dict[str,Any], matrix, lines: Iterable[float]):
    out={}
    provider=evidence.get('hdp_probabilities',{})
    for line in lines:
        key=str(line); base=asian_hdp_from_matrix(matrix,float(line))
        item=provider.get(key) if isinstance(provider,dict) else None
        result=dict(base)
        if isinstance(item,dict):
            for side in ('Home','Away'):
                pv=prob(item.get(side))
                if pv is not None:
                    # blend only the market side; then cap to valid probability.
                    result[side]=clamp(0.75*base[side]+0.25*pv)
        out[key]=result
    return out


def market_edge(probability, odds):
    try:
        o=float(odds)
        if o<=1:return None
        return probability-(1/o)
    except Exception:return None
