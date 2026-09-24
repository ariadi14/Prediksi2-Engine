"""V20.78.37 activate probability engine only after validated fixture evidence."""
from v20_78_32_evidence_probability import EvidenceProbabilityGate
class ProbabilityActivation:
    def __init__(self): self.gate=EvidenceProbabilityGate()
    def run(self, fixture_key, evidence, markets):
        if evidence.get('status')!='ENRICHED': return {'status':'INSUFFICIENT_DATA','warning':'EVIDENCE_NOT_ENRICHED','visible_candidates':[]}
        payload=evidence.get('payload') or {}
        return self.gate.predict(fixture_key,payload,markets)
