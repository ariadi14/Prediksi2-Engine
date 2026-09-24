"""V20.78.39 provider-aware Team ID -> Fixture ID -> Evidence pipeline.
No fabricated live data. A deterministic mock provider is available only for integration tests.
"""
from __future__ import annotations
from typing import Any, Dict
from v20_78_34_provider_connection import ProviderConnection
from v20_78_35_fixture_validation import validate_fixture
from v20_78_36_evidence_retrieval import EvidenceService
from v20_78_37_probability_activation import ProbabilityActivation

class ProviderAwarePipeline:
    VERSION='V20.78.39'
    def __init__(self, connection=None):
        self.connection=connection or ProviderConnection()
        self.providers=self.connection.providers
        self.ev=EvidenceService(self.providers)
        self.prob=ProbabilityActivation()

    def resolve_identity(self, fixture: Dict[str,Any]):
        out=dict(fixture)
        for side in ('home','away'):
            name=out.get(f'{side}_canonical') or out.get(side)
            if not name: continue
            best=None
            for p in self.providers:
                fn=getattr(p,'resolve_team',None)
                if not fn: continue
                try:
                    r=fn(name)
                except Exception as e:
                    r={'status':'UNRESOLVED','reason':str(e)[:160]}
                if r.get('status') in ('RESOLVED_HIGH','RESOLVED_MEDIUM'):
                    best=r; break
                if best is None: best=r
            if best:
                out[f'{side}_identity']=best
                if best.get('canonical_name'): out[f'{side}_canonical']=best['canonical_name']
                if best.get('provider_ids'): out[f'{side}_provider_ids']=best['provider_ids']
        return out

    def resolve_fixture(self, fixture: Dict[str,Any]):
        f=self.resolve_identity(fixture)
        for p in self.providers:
            fn=getattr(p,'find_fixture',None)
            if not fn: continue
            try: candidates=fn(f) or []
            except Exception: candidates=[]
            for c in candidates:
                v=validate_fixture(f,c)
                if v.get('status')=='VALID':
                    f['fixture_id']=c.get('fixture_id')
                    return f,v
        return f,{'status':'REJECTED','reason':'NO_VALID_PROVIDER_FIXTURE'}

    def run_fixture(self, fixture: Dict[str,Any]):
        f, validation=self.resolve_fixture(fixture)
        if validation.get('status')!='VALID':
            ev={'status':'MISSING','reason':validation.get('reason')}
        else:
            ev=self.ev.fetch(f)
        pred=self.prob.run('|'.join(str(f.get(k,'')) for k in ('competition','home_canonical','away_canonical','match_date','kickoff')),ev,f.get('markets') or [])
        return {'fixture':f,'validation':validation,'evidence':ev,'prediction':pred}
