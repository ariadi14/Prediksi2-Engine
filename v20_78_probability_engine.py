"""V20.78 Adaptive Multi-Model Probability Engine.

Converts football evidence into calibrated market probabilities.
No missing evidence is silently fabricated. Inputs are normalized to [0,1]
and model weights are explicit and inspectable.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import exp, factorial
import math
from typing import Any, Dict, Optional, List, Tuple
from v20_78_5_market_models import dedicated_ou, dedicated_hdp
from v20_78_6_adaptive_weights import dynamic_weights, fit_temperature, apply_temperature
from v20_78_7_consistency import consistency_1x2, uncertainty
from v20_78_51_probability_core import build_true_ensemble
from v20_78_51_market_registry import lock_candidates
from v20_78_51_market_value import enrich_group

EPS=1e-12


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(x)))


def normalize_pair(a: float, b: float) -> Tuple[float,float]:
    s=max(EPS, a+b); return a/s,b/s


def poisson_pmf(k:int, lam:float)->float:
    if lam<0: return 0.0
    return exp(-lam)*(lam**k)/factorial(k)


def expected_goals(e: Dict[str,Any], side:str)->Optional[float]:
    """Estimate lambda from explicit xG or attack/defence inputs.
    xG is preferred; otherwise attack*opponent defence*home factor.
    """
    xg=e.get(f"{side}_xg")
    if xg is not None:
        try:
            x=float(xg)
            if x>=0:return x
        except: pass
    attack=e.get(f"{side}_attack")
    opp="away" if side=="home" else "home"
    defence=e.get(f"{opp}_defence")
    if attack is None or defence is None:return None
    try:
        base=float(attack)*float(defence)
        ha=float(e.get("home_advantage",1.0)) if side=="home" else 1.0
        return max(0.05,base*ha)
    except: return None


def dixon_coles_tau(h:int,a:int,lh:float,la:float,rho:float=-0.08)->float:
    """Low-score Dixon-Coles correction for 0/1 score cells."""
    if h==0 and a==0:return 1-lh*la*rho
    if h==0 and a==1:return 1+lh*rho
    if h==1 and a==0:return 1+la*rho
    if h==1 and a==1:return 1-rho
    return 1.0


def score_matrix(lh:float,la:float,max_goals:int=10,rho:float=-0.08)->List[List[float]]:
    raw=[]
    total=0.0
    for h in range(max_goals+1):
        row=[]
        for a in range(max_goals+1):
            p=poisson_pmf(h,lh)*poisson_pmf(a,la)*dixon_coles_tau(h,a,lh,la,rho)
            p=max(0.0,p); row.append(p); total+=p
        raw.append(row)
    total=max(EPS,total)
    return [[p/total for p in row] for row in raw]


def markets_from_matrix(m):
    home=sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h>a)
    draw=sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h==a)
    away=sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h<a)
    def ou(line):
        over=sum(m[h][a] for h in range(len(m)) for a in range(len(m)) if h+a>line)
        return over,1-over
    return {"1X2":{"Home":home,"Draw":draw,"Away":away},
            "O/U":{str(line):{"Over":ou(line)[0],"Under":ou(line)[1]} for line in (0.5,1.5,2.5,3.5)},
            "HDP":{}}


def hdp_from_matrix(m,line:float):
    # Asian handicap from home perspective; quarter-lines are split.
    home=away=0.0
    for h in range(len(m)):
        for a in range(len(m)):
            d=h-a+line
            if d>0: home+=m[h][a]
            elif d<0: away+=m[h][a]
            else: home+=0.5*m[h][a]; away+=0.5*m[h][a]
    return {"Home":home,"Away":away}


def evidence_probabilities(e:Dict[str,Any])->Dict[str,float]:
    """Turn directional evidence into a probability for HOME.
    Values may be supplied as probabilities or signed advantages (-1..1).
    """
    keys=["form_home_prob","home_away_prob","h2h_home_prob","lineup_home_prob",
          "injury_home_prob","suspension_home_prob","tactical_home_prob","elo_home_prob",
          "ml_home_prob"]
    vals=[]; weights=[]
    weights_map={"form_home_prob":1.0,"home_away_prob":1.0,"h2h_home_prob":0.6,
                 "lineup_home_prob":1.2,"injury_home_prob":0.8,"suspension_home_prob":0.8,
                 "tactical_home_prob":1.0,"elo_home_prob":1.1,"ml_home_prob":1.2}
    for k in keys:
        v=e.get(k)
        if v is None:continue
        try:
            v=float(v)
            if 0<=v<=1: vals.append(v); weights.append(weights_map[k])
        except: pass
    if not vals:return {}
    p=sum(v*w for v,w in zip(vals,weights))/sum(weights)
    return {"context_home":clamp(p),"components":len(vals)}


def implied_probability(odds:Any)->Optional[float]:
    try:
        o=float(odds); return 1/o if o>1 else None
    except:return None


def calibrate(p:float, method:str="identity", temperature:float=1.0)->float:
    # Identity during warm-up. Temperature scaling is available when fitted.
    p=clamp(p)
    if method=="temperature":
        import math
        z=math.log(max(EPS,p)/max(EPS,1-p))/max(EPS,temperature)
        return 1/(1+math.exp(-z))
    return p


@dataclass
class ModelOutput:
    fixture_key:str
    status:str
    home_xg:Optional[float]
    away_xg:Optional[float]
    markets:Dict[str,Any]
    model_components:Dict[str,Any]
    calibration:Dict[str,Any]
    warnings:List[str]


class AdaptiveProbabilityEngine:
    VERSION="V20.78.51"
    def __init__(self,max_goals=10): self.max_goals=max_goals

    def predict(self, fixture_key:str, evidence:Dict[str,Any], market_odds:Optional[Dict[str,Any]]=None)->Dict[str,Any]:
        warnings=[]
        lh=expected_goals(evidence,"home"); la=expected_goals(evidence,"away")
        context=evidence_probabilities(evidence)
        if lh is None or la is None:
            return asdict(ModelOutput(fixture_key,"INSUFFICIENT_DATA",lh,la,{},context,
                                      {"status":"UNCALIBRATED","valid_results":evidence.get("valid_results",0)},
                                      ["EXPECTED_GOALS_DATA_MISSING"]))
        matrix=score_matrix(lh,la,self.max_goals,float(evidence.get("dixon_coles_rho",-0.08)))
        markets=markets_from_matrix(matrix)
        # Dedicated O/U and HDP models: calculated directly from the score matrix,
        # with optional independent provider probabilities blended when explicitly present.
        ou_lines=evidence.get("ou_lines", (0.5,1.5,2.5,3.5))
        hdp_lines=evidence.get("handicap_lines", ( -1.5,-1.0,-0.5,0.0,0.5,1.0,1.5))
        markets["O/U"]=dedicated_ou(evidence, matrix, ou_lines)
        markets["HDP"]=dedicated_hdp(evidence, matrix, hdp_lines)
        # V20.78.51 true ensemble: combine the score matrix with independently
        # supplied 1X2/context models. Missing components are omitted and weights
        # are renormalized. The previous fixed home-only blend is retained only
        # as a compatibility fallback when the new core cannot calculate.
        ensemble=build_true_ensemble(evidence, markets)
        if ensemble.get("status")=="CALCULATED":
            markets["1X2"]=ensemble["probabilities"]
        else:
            s=sum(markets["1X2"].values())
            for k in markets["1X2"]: markets["1X2"][k]/=max(EPS,s)
        model_names=["Poisson","Dixon-Coles","xG","form","home_away","H2H","lineup_absence","Elo","ML_context"]
        weights=ensemble.get("weights", dynamic_weights(evidence,model_names))
        # Recalibrate only when settled WIN/LOSS history is sufficient.
        hist_results=evidence.get("calibration_results",[]) or []
        cal=fit_temperature(hist_results)
        if cal["status"]=="CALIBRATED":
            for line,vals in markets["O/U"].items():
                if isinstance(vals,dict) and "Over" in vals:
                    po=apply_temperature(vals["Over"],cal["temperature"])
                    vals["Over"]=po; vals["Under"]=1-po
            for line,vals in markets["HDP"].items():
                if isinstance(vals,dict):
                    for side in ("Home","Away"):
                        if side in vals:
                            vals[side]=apply_temperature(vals[side],cal["temperature"])
            x=markets["1X2"]
            # temperature-scaling each 1X2 logit relative to the normalized distribution
            logits={k:math.log(max(EPS,v)) / max(EPS,cal["temperature"]) for k,v in x.items()}
            ex={k:math.exp(max(-40,min(40,z))) for k,z in logits.items()}; ss=sum(ex.values())
            markets["1X2"]={k:v/ss for k,v in ex.items()}
        eq=round(__import__('v20_78_6_adaptive_weights',fromlist=['evidence_quality']).evidence_quality(evidence),4)
        # Compare independently supplied model probabilities when available.
        model_probs=evidence.get('model_probabilities',{}) or {}
        if isinstance(model_probs,dict):
            if context.get('context_home') is not None:
                ch=context['context_home']; model_probs={**model_probs,'context':{'Home':ch,'Draw':(1-ch)*0.55,'Away':(1-ch)*0.45}}
        consistency=consistency_1x2(model_probs)
        unc=uncertainty(markets['1X2'], consistency.get('agreement'), eq)
        calibration={**cal,'evidence_quality':eq,'cross_model_consistency':consistency,'uncertainty':unc}
        return asdict(ModelOutput(fixture_key,"CALCULATED",lh,la,markets,
                                  {**context,"models":model_names,"dynamic_weights":weights,"true_ensemble":ensemble},
                                  calibration,warnings))

    def select_visible_markets(self,prediction:Dict[str,Any], visible_markets:List[Dict[str,Any]])->List[Dict[str,Any]]:
        out=[]
        for m in visible_markets:
            market=m.get("market"); sel=m.get("selection"); line=m.get("line")
            p=None
            if market=="1X2": p=prediction.get("markets",{}).get("1X2",{}).get(sel)
            elif market=="O/U": p=prediction.get("markets",{}).get("O/U",{}).get(str(line),{}).get(sel)
            elif market=="HDP": p=prediction.get("markets",{}).get("HDP",{}).get(str(line),{}).get(sel)
            if p is None: continue
            imp=implied_probability(m.get("odds")); edge=p-imp if imp is not None else None
            x=dict(m); x.update({"model_probability":p,"implied_probability":imp,"edge":edge})
            out.append(x)
        return out


    def lock_and_value_visible_markets(self, prediction:Dict[str,Any], visible_markets:List[Dict[str,Any]])->List[Dict[str,Any]]:
        """Evaluate only source-visible candidates, preserving exact market/line/selection."""
        candidates=self.select_visible_markets(prediction, visible_markets)
        locked=lock_candidates(candidates, visible_markets)
        groups={}
        for c in locked:
            groups.setdefault((c.get("market"),c.get("line")),[]).append(c)
        out=[]
        for _,rows in groups.items():
            out.extend(enrich_group(rows))
        return out
