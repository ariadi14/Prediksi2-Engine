"""V20.78 pipeline: V20.77.7 parser/audit foundation + adaptive probability layer."""
from __future__ import annotations
from typing import Any, Dict, List
from v20_78_probability_engine import AdaptiveProbabilityEngine
from v20_78_evidence_collector import EvidenceCollector

class V2078Pipeline:
    VERSION="V20.78"
    def __init__(self, evidence_collector=None):
        self.engine=AdaptiveProbabilityEngine()
        self.evidence_collector=evidence_collector
    def run(self, fixtures:List[Dict[str,Any]], evidence_by_key:Dict[str,Dict[str,Any]]|None=None, time_filter="ALL"):
        evidence_by_key=evidence_by_key or {}
        results=[]
        for f in fixtures:
            key="|".join(str(f.get(k,'')) for k in ('competition','home','away','match_date','kickoff'))
            ev=dict(evidence_by_key.get(key,{}))
            if not ev and self.evidence_collector:
                ev=self.evidence_collector.collect({**f,"fixture_key":key})
            odds={}
            for m in f.get('markets',[]): odds.setdefault(m.get('market'),[]).append(m)
            pred=self.engine.predict(key,ev)
            visible=[]
            for ms in f.get('markets',[]): visible.append(ms)
            if pred.get('status')=='CALCULATED':
                candidates=self.engine.select_visible_markets(pred,visible)
            else:candidates=[]
            results.append({'fixture':f,'evidence':ev,'prediction':pred,'visible_candidates':candidates})
        return {'engine_version':self.VERSION,'time_filter':time_filter,'time_filter_mode':'MANUAL','fixture_count':len(fixtures),'results':results}
