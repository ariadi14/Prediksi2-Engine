"""V20.78.3 live provider adapters and automatic evidence enrichment.
Provider-neutral, with concrete adapters for OpenFoot and API-Football.
No fabricated values; unavailable fields remain missing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json, os

class JSONHTTP:
    def __init__(self, base_url:str, token:Optional[str]=None, token_header:str="Authorization", timeout:int=12):
        self.base_url=base_url.rstrip('/'); self.token=token; self.token_header=token_header; self.timeout=timeout
    def get(self, path:str, params:Optional[Dict[str,Any]]=None):
        url=self.base_url+path
        if params:
            url += ('&' if '?' in url else '?') + urlencode({k:v for k,v in params.items() if v is not None})
        headers={"Accept":"application/json"}
        if self.token:
            if self.token_header.lower()=="authorization": headers[self.token_header]="Bearer "+self.token
            else: headers[self.token_header]=self.token
        req=Request(url,headers=headers,method="GET")
        with urlopen(req,timeout=self.timeout) as r:
            return json.loads(r.read().decode('utf-8'))

class OpenFootProvider:
    name="openfoot"
    def __init__(self, token:Optional[str]=None):
        self.http=JSONHTTP("https://openfootapi.com",token)
    def _search(self,q):
        try:
            d=self.http.get('/v1/search',{'q':q})
            return d.get('data',[]) if isinstance(d,dict) else []
        except Exception:return []
    def fetch(self,fixture):
        home=fixture.get('home'); away=fixture.get('away')
        out={"provider":"openfoot","fixture_match":None}
        if not home or not away:return out
        matches=[]
        try:
            # Search by both team names; provider search is used only to resolve stable IDs.
            hs=self._search(home); as_=self._search(away)
            hid=hs[0].get('id') if hs else None; aid=as_[0].get('id') if as_ else None
            q=' '.join([home,away]).strip()
            ms=self._search(q)
            for m in ms:
                if isinstance(m,dict) and ('homeTeam' in m or 'awayTeam' in m): matches.append(m)
            if matches:
                m=matches[0]; out['fixture_match']=m; mid=m.get('id')
                if mid:
                    for path,key in [('/v1/matches/{}/xg','xg'),('/v1/matches/{}/lineups','lineups'),('/v1/odds?matchId={}','odds')]:
                        try: out[key]=self.http.get(path.format(mid))
                        except Exception: pass
        except Exception: pass
        return out

class APIFootballProvider:
    name="api-football"
    def __init__(self, api_key:Optional[str]=None):
        self.http=JSONHTTP("https://v3.football.api-sports.io",api_key,"x-apisports-key")
    def _first(self,d):
        r=d.get('response',[]) if isinstance(d,dict) else []
        return r[0] if r else None
    def search_teams(self,name):
        """Return normalized provider team candidates for identity resolution."""
        try:
            d=self.http.get('/teams',{'search':name})
            rows=d.get('response',[]) if isinstance(d,dict) else []
            out=[]
            for r in rows:
                t=r.get('team',{})
                if t.get('id') is not None:
                    out.append({'name':t.get('name'), 'country':t.get('country'), 'provider_ids':{'api-football':t.get('id')}, 'national':t.get('national')})
            return out
        except Exception:
            return []

    def _fixtures_for_date(self, date):
        if not date: return []
        cache = getattr(self, '_fixture_date_cache', None)
        if cache is None:
            cache = {}
            self._fixture_date_cache = cache
        if date in cache: return cache[date]
        try:
            d = self.http.get('/fixtures', {'date': date})
            rows = d.get('response', []) if isinstance(d, dict) else []
            cache[date] = rows
            return rows
        except Exception as ex:
            cache[date] = []
            self._last_fixture_error = str(ex)[:300]
            return []

    @staticmethod
    def _norm_fixture_team(value):
        import unicodedata, re
        x = unicodedata.normalize('NFKD', str(value or ''))
        x = ''.join(c for c in x if not unicodedata.combining(c))
        return re.sub(r'[^a-z0-9]', '', x.lower())

    def find_fixture(self, fixture):
        home = fixture.get('home_canonical') or fixture.get('home')
        away = fixture.get('away_canonical') or fixture.get('away')
        date = fixture.get('match_date')
        if not home or not away or not date: return []
        rows = self._fixtures_for_date(date)
        hn, an = self._norm_fixture_team(home), self._norm_fixture_team(away)
        from rapidfuzz import fuzz
        scored = []
        for f in rows:
            h = f.get('teams', {}).get('home', {})
            a = f.get('teams', {}).get('away', {})
            hs, aws = self._norm_fixture_team(h.get('name')), self._norm_fixture_team(a.get('name'))
            home_score, away_score = fuzz.ratio(hn, hs), fuzz.ratio(an, aws)
            if home_score >= 82 and away_score >= 82:
                fixture_date = str((f.get('fixture') or {}).get('date', ''))
                kickoff_wib = None
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
                    kickoff_wib = dt.astimezone(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%dT%H:%M:%S%z')
                except Exception: pass
                scored.append((home_score + away_score, {
                    'fixture_id': (f.get('fixture') or {}).get('id'),
                    'home_name': h.get('name'), 'away_name': a.get('name'),
                    'date': fixture_date[:10], 'kickoff_utc': fixture_date,
                    'kickoff_wib': kickoff_wib,
                    'competition': (f.get('league') or {}).get('name'),
                    'home_score': round(home_score, 1), 'away_score': round(away_score, 1),
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [scored[0][1]] if scored else []

    def resolve_team(self,name):
        try:
            d=self.http.get('/teams',{'search':name})
            rows=d.get('response',[]) if isinstance(d,dict) else []
            if not rows: return {'status':'UNRESOLVED','raw':name}
            import re,unicodedata
            def n(x):
                x=unicodedata.normalize('NFKD',str(x or '')); x=''.join(c for c in x if not unicodedata.combining(c)); return re.sub(r'[^a-z0-9]','',x.lower())
            q=n(name); scored=[]
            from rapidfuzz import fuzz
            for r in rows:
                t=r.get('team',{}); score=fuzz.ratio(q,n(t.get('name',''))); scored.append((score,t))
            scored.sort(key=lambda x:x[0],reverse=True); score,t=scored[0]
            second=scored[1][0] if len(scored)>1 else 0
            if score < 80 or score-second < 5: return {'status':'AMBIGUOUS','raw':name,'score':score,'second_score':second}
            return {'status':'RESOLVED_HIGH' if score>=92 else 'RESOLVED_MEDIUM','raw':name,'canonical_name':t.get('name'),'score':score,'provider_ids':{'api-football':t.get('id')},'country':t.get('country')}
        except Exception as ex:
            return {'status':'UNRESOLVED','raw':name,'reason':str(ex)[:200]}

    def fetch(self,fixture):
        home=fixture.get('home_canonical') or fixture.get('home'); away=fixture.get('away_canonical') or fixture.get('away'); date=fixture.get('match_date')
        out={"provider":"api-football","fixture_match":None}
        if not home or not away:return out
        try:
            params={'date':date} if date else ({'team':fixture.get('home_provider_ids',{}).get('api-football'),'next':50} if fixture.get('home_provider_ids',{}).get('api-football') else {'next':50})
            d=self.http.get('/fixtures',params)
            candidates=d.get('response',[]) if isinstance(d,dict) else []
            def norm(s): return ''.join(c.lower() for c in str(s) if c.isalnum())
            hn,an=norm(home),norm(away)
            best=None
            for f in candidates:
                h=norm(f.get('teams',{}).get('home',{}).get('name','')); a=norm(f.get('teams',{}).get('away',{}).get('name',''))
                if h==hn and a==an: best=f; break
                if (hn in h or h in hn) and (an in a or a in an): best=f
            if not best:return out
            out['fixture_match']=best; fid=best.get('fixture',{}).get('id')
            if not fid:return out
            for path,key in [('/predictions', 'predictions'),('/fixtures/lineups','lineups'),('/injuries','injuries'),('/fixtures/statistics','statistics'),('/fixtures/headtohead','h2h'),('/odds','odds')]:
                try:
                    if path=='/predictions': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/fixtures/lineups': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/injuries': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/fixtures/statistics': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/fixtures/headtohead':
                        hi=best.get('teams',{}).get('home',{}).get('id'); ai=best.get('teams',{}).get('away',{}).get('id')
                        d2=self.http.get(path,{'h2h':f'{hi}-{ai}','last':10})
                    else: d2=self.http.get(path,{'fixture':fid})
                    out[key]=d2
                except Exception as ex: out.setdefault('errors',[]).append(str(ex)[:160])
        except Exception as ex: out['errors']=[str(ex)[:300]]
        return out

def flatten_provider_payload(raw:Dict[str,Any])->Dict[str,Any]:
    """Extract only evidence substantiated by a provider payload.
    Supports normalized direct fields and native API payloads.
    """
    out={}
    direct_keys=("home_xg","away_xg","home_attack","away_attack","home_defence","away_defence",
                 "form_home_prob","home_away_prob","h2h_home_prob","lineup_home_prob",
                 "injury_home_prob","suspension_home_prob","tactical_home_prob","elo_home_prob",
                 "ml_home_prob","home_advantage","dixon_coles_rho","evidence_quality")
    for k in direct_keys:
        if raw.get(k) is not None:
            try: out[k]=float(raw[k])
            except: pass
    pred=(raw.get('predictions') or {}).get('response',[]) if isinstance(raw.get('predictions'),dict) else []
    if pred:
        p=pred[0]
        pct=p.get('percent') or {}
        if pct.get('home') is not None:
            try: out['ml_home_prob']=float(pct['home'])/100
            except: pass
        comp=p.get('comparison') or {}
        # API-Football prediction comparison can contain attack/defence percentages.
        try:
            atk=comp.get('att') or {}
            if atk.get('home') is not None and atk.get('away') is not None:
                out['home_attack']=float(atk['home'])/100; out['away_attack']=float(atk['away'])/100
        except Exception: pass
        try:
            de=comp.get('def') or {}
            if de.get('home') is not None and de.get('away') is not None:
                out['home_defence']=float(de['home'])/100; out['away_defence']=float(de['away'])/100
        except Exception: pass
    xg=raw.get('xg')
    if isinstance(xg,dict):
        data=xg.get('data') or xg.get('response') or []
        if isinstance(data,dict): data=[data]
        # Accept common OpenFoot team-total shapes without inventing names.
        for item in data:
            if not isinstance(item,dict):continue
            if item.get('home') is not None and item.get('away') is not None:
                try: out['home_xg']=float(item['home']); out['away_xg']=float(item['away']); break
                except: pass
            if item.get('homeXg') is not None and item.get('awayXg') is not None:
                try: out['home_xg']=float(item['homeXg']); out['away_xg']=float(item['awayXg']); break
                except: pass
    return out

class LiveEvidenceEnricher:
    VERSION="V20.78.3"
    def __init__(self,providers:List[Any]): self.providers=providers
    def enrich(self,fixture:Dict[str,Any]):
        evidence={}; provenance={}; errors=[]
        for p in self.providers:
            try:
                raw=p.fetch(fixture) or {}; flat=flatten_provider_payload(raw)
                for k,v in flat.items():
                    provenance.setdefault(k,[]).append({'source':p.name,'value':v,'confidence':1.0})
                    if k not in evidence:evidence[k]=v
            except Exception as ex: errors.append({'source':getattr(p,'name','unknown'),'error':str(ex)[:300]})
        # Confidence-weighted merge + conflict detection.
        conflicts=[]
        for k,items in provenance.items():
            vals=[float(i['value']) for i in items]
            if vals:
                evidence[k]=sum(vals)/len(vals)
                if k.endswith('_prob') and max(vals)-min(vals)>0.20:
                    conflicts.append({'field':k,'spread':max(vals)-min(vals),'sources':[i['source'] for i in items]})
        evidence['evidence_provenance']=provenance
        evidence['evidence_sources']=sorted(set(i['source'] for xs in provenance.values() for i in xs))
        evidence['evidence_conflicts']=conflicts
        evidence['evidence_status']='CONFLICT' if conflicts else ('VERIFIED' if len(evidence['evidence_sources'])>=2 else ('SINGLE_SOURCE' if evidence['evidence_sources'] else 'MISSING'))
        evidence['collector_errors']=errors
        return evidence
