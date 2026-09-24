"""V20.78.4 Evidence-weighted market ensemble.
Combines score-matrix probabilities with independent context probabilities when present.
No missing values are fabricated; every blended component is recorded.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import math


def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,float(x)))

def prob(v):
    try:
        x=float(v); x=x/100 if 1<x<=100 else x
        return x if 0<=x<=1 else None
    except: return None

def normalize3(h,d,a):
    s=max(1e-12,h+d+a); return h/s,d/s,a/s

def weighted_mean(items):
    items=[(float(v),max(0,float(w))) for v,w in items if v is not None]
    if not items:return None
    den=sum(w for _,w in items)
    return sum(v*w for v,w in items)/den if den else sum(v for v,_ in items)/len(items)

class EvidenceWeightedEnsemble:
    VERSION='V20.78.4'
    DEFAULT_WEIGHTS={'score_matrix':0.45,'xg_model':0.15,'form':0.10,'elo':0.10,'lineup':0.10,'ml':0.10}

    def __init__(self, weights=None):
        self.weights={**self.DEFAULT_WEIGHTS,**(weights or {})}

    def _context_1x2(self,e):
        # Accept explicit 1X2 probabilities from providers; otherwise derive Home probability
        # from existing directional context fields. Draw is kept only when explicitly supplied.
        explicit=e.get('model_1x2')
        if isinstance(explicit,dict):
            h,d,a=(prob(explicit.get('Home')),prob(explicit.get('Draw')),prob(explicit.get('Away')))
            if None not in (h,d,a): return normalize3(h,d,a)
        hp=[]
        for key,weight in [('form_home_prob',.10),('home_away_prob',.10),('h2h_home_prob',.05),('lineup_home_prob',.10),('injury_home_prob',.08),('suspension_home_prob',.05),('tactical_home_prob',.10),('elo_home_prob',.10),('ml_home_prob',.10)]:
            v=prob(e.get(key));
            if v is not None: hp.append((v,weight))
        if not hp:return None
        h=weighted_mean(hp)
        # Only derive draw/away split if the provider supplies it; otherwise use score matrix upstream.
        return h

    def blend_1x2(self, matrix, e):
        base=(matrix['Home'],matrix['Draw'],matrix['Away'])
        ctx=self._context_1x2(e)
        if ctx is None:return normalize3(*base),{'components':['score_matrix'],'weights':{'score_matrix':1.0}}
        if isinstance(ctx,tuple):
            w=clamp(float(e.get('explicit_context_weight',.30)),0,.60)
            return normalize3(*(base[i]*(1-w)+ctx[i]*w for i in range(3))),{'components':['score_matrix','explicit_context'],'weights':{'score_matrix':1-w,'explicit_context':w}}
        # Home-only context: move probability mass from draw/away proportionally.
        w=clamp(float(e.get('context_weight',.25)),0,.50); h=base[0]*(1-w)+ctx*w
        rem=max(1e-12,1-h); old=max(1e-12,1-base[0])
        return normalize3(h,base[1]*rem/old,base[2]*rem/old),{'components':['score_matrix','directional_context'],'weights':{'score_matrix':1-w,'directional_context':w}}

    def market_confidence(self, selected_prob, evidence):
        p=clamp(selected_prob)
        sources=len(evidence.get('evidence_sources',[]) or [])
        status=evidence.get('evidence_status','MISSING')
        completeness=sum(1 for k in ('home_xg','away_xg','form_home_prob','elo_home_prob','h2h_home_prob','lineup_home_prob') if evidence.get(k) is not None)/6
        quality={'MISSING':0.35,'SINGLE_SOURCE':0.55,'CONFLICT':0.60,'VERIFIED':0.80}.get(status,0.45)
        source_factor=min(1.0,0.6+0.15*sources)
        strength=abs(p-0.5)*2
        score=100*(0.45*quality+0.25*source_factor+0.20*completeness+0.10*strength)
        return round(clamp(score/100)*100,1)
