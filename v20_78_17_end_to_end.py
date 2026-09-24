"""V20.78.28 full end-to-end integration.
Screenshot -> OCR -> Team Identity Resolution -> Fixture/Evidence -> Probability -> Parlay.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from typing import Any,Dict,List
import os,time
from fast_pelangi_parser import FastPelangiParser
from v20_78_probability_engine import AdaptiveProbabilityEngine
from v20_78_3_live_providers import APIFootballProvider,OpenFootProvider,LiveEvidenceEnricher
from v20_78_16_decision_engine import run_prediction
from v20_78_26_historical_provider import HistoricalEvidenceProvider
from v20_78_28_team_identity import TeamIdentityResolver, clean_name

VERSION='V20.78.28'

class EndToEndEngine:
    def __init__(self,providers=None,max_workers=6,provider_timeout=8):
        self.parser=FastPelangiParser(); self.engine=AdaptiveProbabilityEngine()
        self.providers=providers or []; self.max_workers=max_workers; self.provider_timeout=provider_timeout
        self.identity=TeamIdentityResolver()
        self._load_identity_catalog()

    def _load_identity_catalog(self):
        catalog=[]
        # Historical CSV is a useful local identity dictionary, not live evidence.
        for p in [os.getenv('FOOTBALL_DATA_CSV')]:
            if p and os.path.exists(p):
                try:
                    import pandas as pd
                    d=pd.read_csv(p,usecols=['HomeTeam','AwayTeam'])
                    names=sorted(set(d['HomeTeam'].dropna().astype(str)) | set(d['AwayTeam'].dropna().astype(str)))
                    catalog += [{'name':n,'aliases':[]} for n in names]
                except Exception: pass
        # Keep built-in aliases available even without a local dataset.
        self.identity=TeamIdentityResolver(catalog)

    @staticmethod
    def key(f): return '|'.join(str(f.get(k,'')) for k in ('competition','home_canonical','away_canonical','match_date','kickoff'))

    def _resolve_fixture(self,f):
        # For live providers, ask API-Football for team identities if configured.
        for p in self.providers:
            if getattr(p,'name','')=='api-football':
                try:
                    h=p.resolve_team(f.get('home','')); a=p.resolve_team(f.get('away',''))
                    hc=h.get('canonical_name') if h else None; ac=a.get('canonical_name') if a else None
                    if hc: f['home_canonical']=hc; f['home_provider_ids']=h.get('provider_ids',{})
                    if ac: f['away_canonical']=ac; f['away_provider_ids']=a.get('provider_ids',{})
                    f['provider_identity']={'home':h,'away':a}
                except Exception: pass
        if not f.get('home_canonical') or not f.get('away_canonical'):
            r=self.identity.resolve_fixture(f)
            f=r
        return f

    def _enrich_one(self,f):
        if not self.providers:return {}
        return LiveEvidenceEnricher(self.providers).enrich(f)

    def enrich_batch(self,fixtures):
        out={}; errors=[]
        if not self.providers:return out,errors
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            jobs={ex.submit(self._enrich_one,f):f for f in fixtures}
            for fut in as_completed(jobs):
                f=jobs[fut]; key=self.key(f)
                try: out[key]=fut.result()
                except Exception as e: errors.append({'fixture_key':key,'error':str(e)[:300]})
        return out,errors

    def _merge_resolved(self, fixtures):
        merged={}
        for f in fixtures:
            hk=f.get('home_canonical') or clean_name(f.get('home',''))
            ak=f.get('away_canonical') or clean_name(f.get('away',''))
            key=(clean_name(f.get('competition','')), hk.lower(), ak.lower(), f.get('match_date') or '', f.get('kickoff') or '')
            if key not in merged:
                g=dict(f); g['markets']=list(f.get('markets',[])); merged[key]=g
            else:
                g=merged[key]; seen={(m.get('market'),m.get('selection'),m.get('line'),m.get('odds')) for m in g.get('markets',[])}
                for m in f.get('markets',[]):
                    sig=(m.get('market'),m.get('selection'),m.get('line'),m.get('odds'))
                    if sig not in seen: g['markets'].append(m); seen.add(sig)
                g['source_image_ids']=sorted(set(g.get('source_image_ids',[])+f.get('source_image_ids',[])))
        return list(merged.values())

    def run_fixtures(self,fixtures,evidence_by_key=None,time_filter='ALL',parlay_size=7):
        fixtures=[self._resolve_fixture(dict(f)) for f in fixtures]
        fixtures=self._merge_resolved(fixtures)
        evidence_by_key=dict(evidence_by_key or {})
        live,errors=self.enrich_batch([f for f in fixtures if self.key(f) not in evidence_by_key and f.get('identity_status')!='UNRESOLVED'])
        evidence_by_key.update(live)
        prepared=[]
        for f in fixtures:
            key=self.key(f); ev=evidence_by_key.get(key,{})
            pred=self.engine.predict(key,ev)
            visible=f.get('markets',[])
            candidates=self.engine.select_visible_markets(pred,visible) if pred.get('status')=='CALCULATED' else []
            prepared.append({'fixture_key':key,'fixture':f,'evidence':ev,'prediction':pred,'visible_candidates':candidates})
        final=run_prediction([{'fixture_key':x['fixture_key'],'prediction':x['prediction'],'visible_markets':x['visible_candidates']} for x in prepared],parlay_size=parlay_size)
        bykey={x['fixture_key']:x for x in prepared}
        for r in final['results']:
            if r['fixture_key'] in bykey: bykey[r['fixture_key']]['market_candidates']=r['market_candidates']
        return {'version':VERSION,'time_filter':time_filter,'time_filter_mode':'MANUAL','fixtures_processed':len(fixtures),
                'evidence_enriched':sum(1 for v in live.values() if v.get('evidence_status') not in ('MISSING',None)),
                'provider_errors':errors,'identity_resolved':sum(1 for f in fixtures if f.get('identity_status')=='RESOLVED'),
                'identity_unresolved':sum(1 for f in fixtures if f.get('identity_status')!='RESOLVED'),
                'results':prepared,'decision':final}

    def run_images(self,paths,time_filter='ALL',evidence_by_key=None,parlay_size=7):
        t=time.time(); replay=self.parser.replay(paths,time_filter)
        result=self.run_fixtures(replay['fixtures'],evidence_by_key,time_filter,parlay_size)
        result.update({'images':len(paths),'parsed_market_rows':replay['parsed_market_rows'],'unique_fixtures':len(replay['fixtures']),
                       'ocr_seconds':round(time.time()-t,3),'parser_replay':replay})
        return result

def default_providers(historical_csv=None):
    ps=[]
    if os.getenv('API_FOOTBALL_KEY'): ps.append(APIFootballProvider(os.getenv('API_FOOTBALL_KEY')))
    if os.getenv('OPENFOOT_TOKEN'): ps.append(OpenFootProvider(os.getenv('OPENFOOT_TOKEN')))
    hp=historical_csv or os.getenv('FOOTBALL_DATA_CSV')
    if hp and os.path.exists(hp): ps.append(HistoricalEvidenceProvider(hp))
    return ps
