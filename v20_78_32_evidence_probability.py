"""V20.78.32 evidence-to-probability gate."""
from __future__ import annotations
from typing import Any,Dict
from v20_78_probability_engine import AdaptiveProbabilityEngine
class EvidenceProbabilityGate:
    def __init__(self): self.engine=AdaptiveProbabilityEngine()
    def predict(self,key,evidence,visible_markets):
        if evidence.get('evidence_status')=='MISSING':
            return {'status':'INSUFFICIENT_DATA','warning':'FIXTURE_EVIDENCE_MISSING','fixture_key':key,'visible_candidates':[]}
        pred=self.engine.predict(key,evidence)
        candidates=self.engine.select_visible_markets(pred,visible_markets) if pred.get('status')=='CALCULATED' else []
        pred['visible_candidates']=candidates
        return pred
