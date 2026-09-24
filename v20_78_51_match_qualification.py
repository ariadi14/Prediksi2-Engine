"""Conservative candidate qualification for visible source markets."""
from __future__ import annotations
from typing import Any, Dict

def qualify(c: Dict[str,Any], min_probability=0.50, min_edge=0.0, min_ev=0.0, min_confidence='MEDIUM') -> Dict[str,Any]:
    x=dict(c); reasons=[]
    if not x.get('source_market_locked'): reasons.append('MARKET_NOT_AVAILABLE_IN_SOURCE')
    p=x.get('model_probability'); edge=x.get('edge'); ev=x.get('ev')
    if p is None or float(p)<min_probability: reasons.append('PROBABILITY_BELOW_THRESHOLD')
    if edge is None or float(edge)<min_edge: reasons.append('EDGE_BELOW_THRESHOLD')
    if ev is None or float(ev)<min_ev: reasons.append('EV_BELOW_THRESHOLD')
    conf=str(x.get('data_confidence','MEDIUM')).upper()
    rank={'LOW':0,'MEDIUM':1,'HIGH':2,'INSUFFICIENT':-1};
    if rank.get(conf,-1)<rank.get(min_confidence,1): reasons.append('DATA_CONFIDENCE_LOW')
    x['qualified']=not reasons; x['qualification_reasons']=reasons
    return x

def confidence(evidence: Dict[str,Any]) -> str:
    status=str(evidence.get('evidence_status','MISSING')).upper()
    freshness=float(evidence.get('freshness_score',0) or 0)
    resolved=bool(evidence.get('fixture_resolved', evidence.get('fixture_id')))
    if status=='VERIFIED' and resolved and freshness>=0.8:return 'HIGH'
    if status in {'VERIFIED','SINGLE_SOURCE'} and resolved:return 'MEDIUM'
    if status=='INSUFFICIENT':return 'INSUFFICIENT'
    return 'LOW'
