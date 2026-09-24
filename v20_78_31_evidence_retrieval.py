"""V20.78.31 evidence retrieval after fixture identity is established."""
from __future__ import annotations
from typing import Any,Dict,List
class EvidenceRetrieval:
    def __init__(self, providers:List[Any]): self.providers=providers
    def fetch(self, fixture):
        evidence={}; errors=[]; sources=[]
        if fixture.get('fixture_id') is None:
            return {'evidence_status':'MISSING','retrieval_block':'NO_FIXTURE_ID'}
        for p in self.providers:
            try:
                raw=p.fetch(fixture) or {}
                from v20_78_3_live_providers import flatten_provider_payload
                flat=flatten_provider_payload(raw)
                for k,v in flat.items(): evidence.setdefault(k,v)
                if flat: sources.append(getattr(p,'name','unknown'))
            except Exception as e: errors.append({'provider':getattr(p,'name','unknown'),'error':str(e)[:240]})
        evidence['evidence_sources']=sources
        evidence['collector_errors']=errors
        evidence['evidence_status']='SINGLE_SOURCE' if len(sources)==1 else ('VERIFIED' if len(sources)>=2 else 'MISSING')
        return evidence
