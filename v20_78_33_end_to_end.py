"""V20.78.33 real replay checkpoint: screenshot -> identity -> fixture -> evidence -> probability -> visible market -> parlay."""
from __future__ import annotations
import os,time
from typing import Any,Dict,List
from fast_pelangi_parser import FastPelangiParser
from v20_78_28_team_identity import TeamIdentityResolver,clean_name
from v20_78_29_provider_identity import ProviderAwareTeamResolver
from v20_78_30_fixture_resolution import resolve_fixture_id
from v20_78_31_evidence_retrieval import EvidenceRetrieval
from v20_78_32_evidence_probability import EvidenceProbabilityGate
from v20_78_16_decision_engine import run_prediction

VERSION='V20.78.33'
class V33Engine:
    def __init__(self,providers=None,catalog=None,historical_csv=None):
        self.parser=FastPelangiParser(); self.providers=providers or []
        self.api=next((p for p in self.providers if getattr(p,'name','')=='api-football'),None)
        if catalog is None:
            catalog=[]
            hp=historical_csv or os.getenv('FOOTBALL_DATA_CSV') or '/mnt/data/v20_78_24_testdata/FootballData_GLOBAL_MASTER_2012_2027.csv'
            if os.path.exists(hp):
                try:
                    import pandas as pd
                    d=pd.read_csv(hp,usecols=['HomeTeam','AwayTeam'])
                    names=sorted(set(d['HomeTeam'].dropna().astype(str))|set(d['AwayTeam'].dropna().astype(str)))
                    catalog=[{'name':n,'aliases':[]} for n in names]
                except Exception: pass
        self.identity=ProviderAwareTeamResolver(self.api,catalog)
        self.gate=EvidenceProbabilityGate()
        self.retriever=EvidenceRetrieval(self.providers)
    def resolve(self,f):
        g=dict(f)
        h=self.identity.resolve(g.get('home',''),g.get('competition','')); a=self.identity.resolve(g.get('away',''),g.get('competition',''))
        g['identity']={'home':h,'away':a}; g['identity_status']='RESOLVED' if h.get('status','').startswith('RESOLVED') and a.get('status','').startswith('RESOLVED') else 'UNRESOLVED'
        if g['identity_status']=='RESOLVED':
            g['home_canonical']=h.get('canonical_name'); g['away_canonical']=a.get('canonical_name')
            g['home_provider_ids']=h.get('provider_ids',{}); g['away_provider_ids']=a.get('provider_ids',{})
            fr=resolve_fixture_id(g,self.api)
            g['fixture_resolution']=fr
            if fr.get('status')=='RESOLVED': g['fixture_id']=fr.get('fixture_id')
        return g
    def run(self,paths,time_filter='ALL'):
        t=time.time(); replay=self.parser.replay(paths,time_filter); results=[]
        for f in replay['fixtures']:
            g=self.resolve(f)
            ev=self.retriever.fetch(g) if g.get('fixture_id') else {'evidence_status':'MISSING','retrieval_block':'NO_FIXTURE_ID'}
            pred=self.gate.predict(self._key(g),ev,g.get('markets',[]))
            results.append({'fixture':g,'evidence':ev,'prediction':pred})
        final=run_prediction([{'fixture_key':self._key(x['fixture']),'prediction':x['prediction'],'visible_markets':x['prediction'].get('visible_candidates',[])} for x in results],parlay_size=7)
        return {'version':VERSION,'time_filter_mode':'MANUAL','time_filter':time_filter,'images':len(paths),'parsed_market_rows':replay['parsed_market_rows'],'unique_fixtures':len(results),'identity_resolved':sum(x['fixture'].get('identity_status')=='RESOLVED' for x in results),'fixture_resolved':sum(x['fixture'].get('fixture_id') is not None for x in results),'evidence_enriched':sum(x['evidence'].get('evidence_status')!='MISSING' for x in results),'calculated':sum(x['prediction'].get('status')=='CALCULATED' for x in results),'no_bet':(final.get('parlay') or {}).get('status')=='NO_BET','decision':final,'results':results,'seconds':round(time.time()-t,3),'parser_replay':replay}
    @staticmethod
    def _key(f): return '|'.join(str(f.get(k,'')) for k in ('competition','home_canonical','away_canonical','match_date','kickoff'))
