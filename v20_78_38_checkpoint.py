"""V20.78.38 real replay checkpoint runner."""
import time
from v20_78_33_end_to_end import V33Engine
from v20_78_34_provider_connection import ProviderConnection
from v20_78_35_fixture_validation import validate_fixture
from v20_78_36_evidence_retrieval import EvidenceService
from v20_78_37_probability_activation import ProbabilityActivation

class V38Engine:
    VERSION='V20.78.38'
    def __init__(self, connection=None):
        self.connection=connection or ProviderConnection()
        self.base=V33Engine(providers=self.connection.providers)
        self.ev=EvidenceService(self.connection.providers); self.prob=ProbabilityActivation()
    def run(self, paths, time_filter='ALL'):
        t=time.time()
        # Reuse V33 replay parser by running with providers disabled, then enrich here.
        raw=self.base.run(paths,time_filter)
        results=[]
        for item in raw['results']:
            f=dict(item['fixture']); fr=f.get('fixture_resolution') or {}
            candidate=(fr.get('match') if fr.get('status')=='RESOLVED' else None)
            validation=validate_fixture(f,candidate) if candidate else {'status':'REJECTED','reason':'NO_RESOLVED_CANDIDATE'}
            ev=self.ev.fetch(f) if validation.get('status')=='VALID' else {'status':'MISSING','reason':validation.get('reason')}
            pred=self.prob.run('|'.join(str(f.get(k,'')) for k in ('competition','home_canonical','away_canonical','match_date','kickoff')),ev,f.get('markets') or [])
            results.append({'fixture':f,'validation':validation,'evidence':ev,'prediction':pred})
        return {'version':self.VERSION,'provider_status':self.connection.status(),'images':len(paths),
                'parsed_market_rows':raw['parsed_market_rows'],'unique_fixtures':len(results),
                'identity_resolved':sum(r['fixture'].get('identity_status')=='RESOLVED' for r in results),
                'fixture_resolved':sum(r['validation'].get('status')=='VALID' for r in results),
                'evidence_enriched':sum(r['evidence'].get('status')=='ENRICHED' for r in results),
                'calculated':sum(r['prediction'].get('status')=='CALCULATED' for r in results),
                'results':results,'seconds':round(time.time()-t,3)}
