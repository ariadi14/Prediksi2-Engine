"""V20.78.36 evidence retrieval with provenance and failure isolation."""
from v20_78_3_live_providers import flatten_provider_payload

class EvidenceService:
    def __init__(self, providers): self.providers=providers or []
    def fetch(self, fixture):
        if not fixture.get('fixture_id'): return {'status':'MISSING','reason':'NO_FIXTURE_ID','providers':[]}
        attempts=[]
        merged={}
        for p in self.providers:
            name=getattr(p,'name',p.__class__.__name__)
            try:
                raw=p.fetch(fixture) or {}
                flat=flatten_provider_payload(raw)
                attempts.append({'provider':name,
                                 'ok':bool(raw.get('fixture_match') or flat),
                                 'errors':raw.get('errors',[])})
                if raw.get('fixture_match'): merged['fixture_match']=raw['fixture_match']
                for k,v in flat.items():
                    if v not in (None,{},[]): merged.setdefault(k,v)
            except Exception as e: attempts.append({'provider':name,'ok':False,'errors':[str(e)[:200]]})
        if not merged: return {'status':'UNAVAILABLE','reason':'ALL_PROVIDERS_FAILED_OR_EMPTY','providers':attempts}
        return {'status':'ENRICHED','providers':attempts,'payload':merged}
