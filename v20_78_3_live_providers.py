"""V20.78.3 live provider adapters and automatic evidence enrichment.
Provider-neutral, with concrete adapters for OpenFoot and API-Football.
No fabricated values; unavailable fields remain missing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json, os, time, subprocess

class JSONHTTP:
    def __init__(self, base_url:str, token:Optional[str]=None, token_header:str="Authorization", timeout:int=12):
        self.base_url=base_url.rstrip('/'); self.token=token; self.token_header=token_header; self.timeout=timeout
        self.throttle_seconds = float(os.getenv("API_FOOTBALL_THROTTLE_SECONDS", "0")) if "api-sports.io" in self.base_url else 0.0
        self._last_request_at = 0.0
        self.rate_limit_diagnostics = {}
        self.api_quota_exhausted = False
        self.last_error_diagnostics = {}
    def get(self, path:str, params:Optional[Dict[str,Any]]=None):
        url=self.base_url+path
        if params:
            url += ('&' if '?' in url else '?') + urlencode({k:v for k,v in params.items() if v is not None})
        headers={"Accept":"application/json"}
        # OpenFoot is fronted by Cloudflare. Python urllib otherwise sends
        # its default Python-urllib/<version> signature, which the API edge
        # may reject before the API can return its documented JSON error.
        # Use an explicit, stable application UA; do not retry/bypass 403s.
        if "openfootapi.com" in self.base_url:
            headers["User-Agent"] = "Prediksi2-Engine/20.79 (+https://github.com/ariadi14/Prediksi2-Engine)"
        if self.token:
            if self.token_header.lower()=="authorization": headers[self.token_header]="Bearer "+self.token
            else: headers[self.token_header]=self.token
        if self.throttle_seconds > 0 and self._last_request_at:
            wait = self.throttle_seconds - (time.monotonic() - self._last_request_at)
            if wait > 0:
                time.sleep(wait)
        # OpenFoot documents cURL/fetch as supported clients. The GitHub
        # Actions Python-urllib transport was rejected at the Cloudflare edge
        # with browser_signature_banned even after an explicit User-Agent.
        # Use the system curl client for OpenFoot only; this is a normal API
        # transport, not a retry/bypass mechanism.
        if "openfootapi.com" in self.base_url:
            try:
                cmd=["curl","-sS","-L","--max-time",str(self.timeout),"-H","Accept: application/json"]
                if self.token:
                    cmd += ["-H","Authorization: Bearer " + self.token]
                cmd += ["-w","\\n__OPENFOOT_HTTP_STATUS__:%{http_code}","--url",url]
                proc=subprocess.run(cmd,capture_output=True,text=True,timeout=self.timeout+3)
                self._last_request_at=time.monotonic()
                raw=proc.stdout or ""
                marker="\\n__OPENFOOT_HTTP_STATUS__:"
                if marker in raw:
                    body,status_text=raw.rsplit(marker,1)
                    status=int(status_text.strip() or "0")
                else:
                    body,status=raw,0
                if proc.returncode != 0 and status == 0:
                    raise RuntimeError((proc.stderr or "curl request failed")[:1000])
                try:
                    payload=json.loads(body)
                except Exception:
                    payload={}
                if status >= 400:
                    err=payload.get("error") if isinstance(payload,dict) else None
                    self.last_error_diagnostics={
                        "status_code":status,
                        "error_code":(err or {}).get("code") if isinstance(err,dict) else None,
                        "error_message":(err or {}).get("message") if isinstance(err,dict) else None,
                        "response_body":body[:1000],
                        "rate_limit_diagnostics":dict(self.rate_limit_diagnostics),
                    }
                    raise RuntimeError("HTTP %s: %s" % (status, self.last_error_diagnostics.get("error_code") or self.last_error_diagnostics.get("error_message") or "request_failed"))
                return payload
            except Exception as exc:
                self.last_error_diagnostics = {
                    "status_code": self.last_error_diagnostics.get("status_code"),
                    "error_code": self.last_error_diagnostics.get("error_code") or type(exc).__name__,
                    "error_message": self.last_error_diagnostics.get("error_message") or str(exc)[:1000],
                    "rate_limit_diagnostics":dict(self.rate_limit_diagnostics),
                }
                raise
        req=Request(url,headers=headers,method="GET")
        try:
            with urlopen(req,timeout=self.timeout) as r:
                self._last_request_at = time.monotonic()
                for k,v in r.headers.items():
                    lk=k.lower()
                    if lk in {"x-ratelimit-requests-limit","x-ratelimit-requests-remaining","x-ratelimit-limit","x-ratelimit-remaining"}:
                        self.rate_limit_diagnostics[lk] = v
                payload = json.loads(r.read().decode("utf-8"))
                errors = payload.get("errors") if isinstance(payload, dict) else None
                error_text = json.dumps(errors, ensure_ascii=False).lower() if errors else ""
                quota_markers = (
                    "request limit for the day",
                    "daily request limit",
                    "rate limit exceeded",
                    "too many requests",
                    "quota exceeded",
                )
                if any(marker in error_text for marker in quota_markers):
                    self.api_quota_exhausted = True
                    self.rate_limit_diagnostics["quota_exhausted"] = True
                    self.rate_limit_diagnostics["quota_error"] = str(errors)[:500]
                return payload
        except HTTPError as exc:
            self._last_request_at = time.monotonic()
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            error_obj = None
            try:
                parsed = json.loads(body) if body else {}
                error_obj = parsed.get("error") if isinstance(parsed, dict) else None
            except Exception:
                error_obj = None
            self.last_error_diagnostics = {
                "status_code": int(getattr(exc, "code", 0) or 0),
                "error_code": (error_obj or {}).get("code") if isinstance(error_obj, dict) else None,
                "error_message": (error_obj or {}).get("message") if isinstance(error_obj, dict) else None,
                "response_body": body[:1000],
                "rate_limit_diagnostics": dict(self.rate_limit_diagnostics),
            }
            raise RuntimeError(
                "HTTP %s: %s" % (
                    self.last_error_diagnostics["status_code"],
                    self.last_error_diagnostics.get("error_code") or self.last_error_diagnostics.get("error_message") or "request_failed"
                )
            ) from exc
        except Exception as exc:
            self._last_request_at = time.monotonic()
            self.last_error_diagnostics = {
                "status_code": None,
                "error_code": type(exc).__name__,
                "error_message": str(exc)[:1000],
                "rate_limit_diagnostics": dict(self.rate_limit_diagnostics),
            }
            raise

class OpenFootProvider:
    name="openfoot"
    def __init__(self, token:Optional[str]=None):
        self.http=JSONHTTP("https://openfootapi.com",token)
        self._fixture_date_cache={}
        self._last_fixture_lookup={}

    @staticmethod
    def _norm(value):
        import unicodedata, re
        x=unicodedata.normalize('NFKD',str(value or ''))
        x=''.join(c for c in x if not unicodedata.combining(c))
        return re.sub(r'[^a-z0-9]','',x.lower())

    def _search(self,q):
        try:
            d=self.http.get('/v1/search',{'q':q})
            return d.get('data',[]) if isinstance(d,dict) else []
        except Exception:
            return []

    def resolve_team(self,name):
        rows=[x for x in self._search(name) if isinstance(x,dict) and x.get('id')]
        if not rows:
            return {'status':'UNRESOLVED','raw':name}
        from rapidfuzz import fuzz
        scored=sorted(
            [(max(fuzz.ratio(self._norm(name),self._norm(x.get('name'))),
                  fuzz.WRatio(self._norm(name),self._norm(x.get('name')))),x) for x in rows],
            key=lambda z:z[0], reverse=True)
        score,row=scored[0]
        second=scored[1][0] if len(scored)>1 else 0.0
        if score < 80 or (len(scored)>1 and score-second < 8):
            return {'status':'AMBIGUOUS','raw':name,'score':round(score,1),'second_score':round(second,1)}
        return {
            'status':'RESOLVED_HIGH' if score>=92 else 'RESOLVED_MEDIUM',
            'raw':name,
            'canonical_name':row.get('name'),
            'score':round(score,1),
            'second_score':round(second,1),
            'provider_ids':{'openfoot':row.get('id')},
            'country':row.get('country'),
        }

    def _matches_for_date(self,date):
        if not date: return []
        if date in self._fixture_date_cache: return self._fixture_date_cache[date]
        try:
            d=self.http.get('/v1/matches',{'date':date})
            rows=d.get('data',[]) if isinstance(d,dict) else []
            self._fixture_date_cache[date]=rows if isinstance(rows,list) else []
            self._last_fixture_lookup={
                'date':date,
                'rows':len(self._fixture_date_cache[date]),
                'error':None,
                'api_errors':d.get('error') if isinstance(d,dict) else None,
                'rate_limit_diagnostics':dict(getattr(self.http,'rate_limit_diagnostics',{})),
            }
            return self._fixture_date_cache[date]
        except Exception as ex:
            self._last_fixture_lookup={
                'date':date,'rows':0,'error':str(ex)[:300],
                'exception_type':type(ex).__name__,
                'error_diagnostics':dict(getattr(self.http,'last_error_diagnostics',{})),
                'rate_limit_diagnostics':dict(getattr(self.http,'rate_limit_diagnostics',{})),
            }
            self._fixture_date_cache[date]=[]
            return []

    def find_fixture(self,fixture):
        home=fixture.get('home_canonical') or fixture.get('home')
        away=fixture.get('away_canonical') or fixture.get('away')
        date=fixture.get('match_date')
        if not home or not away or not date: return []
        rows=self._matches_for_date(date)
        from rapidfuzz import fuzz
        hn,an=self._norm(home),self._norm(away)
        scored=[]
        for m in rows:
            h=(m.get('homeTeam') or {})
            a=(m.get('awayTeam') or {})
            hs,aws=self._norm(h.get('name')),self._norm(a.get('name'))
            hs_score=max(fuzz.ratio(hn,hs),fuzz.WRatio(hn,hs))
            as_score=max(fuzz.ratio(an,aws),fuzz.WRatio(an,aws))
            if hs_score>=82 and as_score>=82:
                kickoff=str(m.get('kickoffAt') or '')
                scored.append((hs_score+as_score,{
                    'fixture_id':m.get('id'),
                    'home_name':h.get('name'),
                    'away_name':a.get('name'),
                    'date':kickoff[:10] or date,
                    'kickoff_utc':kickoff,
                    'competition':m.get('competitionName'),
                    'home_id':h.get('id'),
                    'away_id':a.get('id'),
                    'match_mode':'STRONG_BOTH',
                }))
        scored.sort(key=lambda x:x[0],reverse=True)
        self._last_fixture_lookup.update({
            'requested_home':home,'requested_away':away,
            'candidate_count':len(scored),
            'best_fixture_id':scored[0][1].get('fixture_id') if scored else None,
            'best_home_name':scored[0][1].get('home_name') if scored else None,
            'best_away_name':scored[0][1].get('away_name') if scored else None,
            'best_home_score':round(scored[0][1].get('home_score',0),1) if scored else None,
            'best_away_score':round(scored[0][1].get('away_score',0),1) if scored else None,
            'unique_match':len(scored)==1,
        })
        if len(scored)==1:
            return [scored[0][1]]
        return [scored[0][1]] if scored and scored[0][0]>=170 else []

    def fetch(self,fixture):
        home=fixture.get('home_canonical') or fixture.get('home')
        away=fixture.get('away_canonical') or fixture.get('away')
        out={'provider':'openfoot','fixture_match':None}
        if not home or not away: return out
        try:
            mid=fixture.get('fixture_id')
            if not mid:
                found=self.find_fixture(fixture)
                mid=found[0].get('fixture_id') if found else None
            if not mid: return out
            out['fixture_match']={'id':mid,'homeTeam':{'name':home},'awayTeam':{'name':away}}
            context=self.http.get(f'/v1/matches/{mid}/context')
            out['context']=context
            out['rate_limit_diagnostics']=dict(getattr(self.http,'rate_limit_diagnostics',{}))
        except Exception as ex:
            out['errors']=[str(ex)[:300]]
            out['error_diagnostics']=dict(getattr(self.http,'last_error_diagnostics',{}))
            out['rate_limit_diagnostics']=dict(getattr(self.http,'rate_limit_diagnostics',{}))
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
        rows_all = []
        try:
            page = 1
            response_errors = []
            while True:
                d = self.http.get('/fixtures', {'date': date, 'timezone': 'Asia/Jakarta', 'page': page})
                if isinstance(d, dict):
                    response_errors.extend(d.get('errors') or [])
                rows = d.get('response', []) if isinstance(d, dict) else []
                rows_all.extend(rows)
                paging = d.get('paging', {}) if isinstance(d, dict) else {}
                total_pages = int(paging.get('total') or page)
                if page >= total_pages or not rows: break
                page += 1
            # A second, conservative probe without timezone helps distinguish
            # a timezone/query issue from a genuinely empty provider day.
            fallback_rows = []
            fallback_errors = []
            if not rows_all and not getattr(self.http, 'api_quota_exhausted', False):
                try:
                    d2 = self.http.get('/fixtures', {'date': date})
                    fallback_rows = d2.get('response', []) if isinstance(d2, dict) else []
                    fallback_errors = d2.get('errors') or [] if isinstance(d2, dict) else []
                except Exception as ex2:
                    fallback_errors = [str(ex2)[:300]]
                if fallback_rows:
                    rows_all = fallback_rows
            cache[date] = rows_all
            # Keep raw provider fixture rows so evidence enrichment can reuse
            # the exact fixture already obtained during resolution.
            raw_by_id = {}
            for row in rows_all:
                try:
                    rid = (row.get('fixture') or {}).get('id')
                    if rid is not None:
                        raw_by_id[int(rid)] = row
                except Exception:
                    continue
            if raw_by_id:
                self._fixture_raw_by_id = getattr(self, '_fixture_raw_by_id', {})
                self._fixture_raw_by_id.update(raw_by_id)
            self._last_fixture_error = None
            quota_exhausted = bool(getattr(self.http, 'api_quota_exhausted', False))
            if quota_exhausted:
                # A daily quota response is terminal for this run. Do not make
                # the conservative timezone-less fallback request, which would
                # consume another API call without changing the outcome.
                fallback_rows = []
                fallback_errors = []
            self._last_fixture_lookup = {
                'date': date,
                'rows': len(rows_all),
                'pages': page,
                'error': None,
                'api_errors': list(response_errors)[:10] if isinstance(response_errors, list) else [str(response_errors)[:300]],
                'fallback_without_timezone_rows': len(fallback_rows),
                'fallback_without_timezone_errors': list(fallback_errors)[:10] if isinstance(fallback_errors, list) else [str(fallback_errors)[:300]],
                'api_quota_exhausted': quota_exhausted,
                'throttle_seconds': getattr(self.http, 'throttle_seconds', 0.0),
                'rate_limit_diagnostics': dict(getattr(self.http, 'rate_limit_diagnostics', {})),
            }
            return rows_all
        except Exception as ex:
            cache[date] = rows_all
            self._last_fixture_error = str(ex)[:300]
            self._last_fixture_lookup = {
                'date': date,
                'rows': len(rows_all),
                'pages': page,
                'error': self._last_fixture_error,
                'exception_type': type(ex).__name__,
            }
            return rows_all

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
            strong_both = home_score >= 82 and away_score >= 82
            strong_home_only = home_score >= 92 and away_score < 82
            strong_away_only = away_score >= 92 and home_score < 82
            if strong_both or strong_home_only or strong_away_only:
                fixture_date = str((f.get('fixture') or {}).get('date', ''))
                kickoff_wib = None
                try:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
                    kickoff_wib = dt.astimezone(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%dT%H:%M:%S%z')
                except Exception: pass
                mode = ('STRONG_BOTH' if strong_both else 'STRONG_HOME_ONLY' if strong_home_only else 'STRONG_AWAY_ONLY')
                scored.append((home_score + away_score, {
                    'fixture_id': (f.get('fixture') or {}).get('id'),
                    'home_name': h.get('name'), 'away_name': a.get('name'),
                    'date': fixture_date[:10], 'kickoff_utc': fixture_date,
                    'kickoff_wib': kickoff_wib,
                    'competition': (f.get('league') or {}).get('name'),
                    'home_score': round(home_score, 1), 'away_score': round(away_score, 1),
                    'match_mode': mode,
                }))
        scored.sort(key=lambda x: x[0], reverse=True)
        unique_match = len(scored) == 1
        if scored:
            scored[0][1]['unique_match'] = unique_match
        self._last_fixture_lookup = dict(getattr(self, '_last_fixture_lookup', {}))
        self._last_fixture_lookup.update({
            'requested_home': home,
            'requested_away': away,
            'candidate_count': len(scored),
            'best_home_score': scored[0][1]['home_score'] if scored else None,
            'best_away_score': scored[0][1]['away_score'] if scored else None,
            'best_fixture_id': scored[0][1]['fixture_id'] if scored else None,
            'best_home_name': scored[0][1]['home_name'] if scored else None,
            'best_away_name': scored[0][1]['away_name'] if scored else None,
            'best_competition': scored[0][1]['competition'] if scored else None,
            'best_match_mode': scored[0][1].get('match_mode') if scored else None,
            'unique_match': unique_match,
        })
        if not scored:
            return []
        if scored[0][1].get('match_mode') != 'STRONG_BOTH' and not unique_match:
            return []
        return [scored[0][1]]

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
            fid=fixture.get('fixture_id')
            candidates=[]
            if fid:
                cached = getattr(self, '_fixture_raw_by_id', {}).get(int(fid))
                if cached:
                    candidates=[cached]
                else:
                    d=self.http.get('/fixtures',{'id':fid})
                    candidates=d.get('response',[]) if isinstance(d,dict) else []
            if not candidates:
                params={'date':date} if date else ({'team':fixture.get('home_provider_ids',{}).get('api-football'),'next':50} if fixture.get('home_provider_ids',{}).get('api-football') else {'next':50})
                d=self.http.get('/fixtures',params)
                candidates=d.get('response',[]) if isinstance(d,dict) else []
            def norm(s): return ''.join(c.lower() for c in str(s) if c.isalnum())
            hn,an=norm(home),norm(away)
            best=None
            if fid and candidates:
                best=candidates[0]
            else:
                for f in candidates:
                    h=norm(f.get('teams',{}).get('home',{}).get('name','')); a=norm(f.get('teams',{}).get('away',{}).get('name',''))
                    if h==hn and a==an: best=f; break
                    if (hn in h or h in hn) and (an in a or a in an): best=f
            if not best:return out
            out['fixture_match']=best; fid=best.get('fixture',{}).get('id')
            if not fid:return out

            league = best.get('league') or {}
            league_id = league.get('id')
            season = league.get('season')
            home_id = (best.get('teams') or {}).get('home',{}).get('id')
            away_id = (best.get('teams') or {}).get('away',{}).get('id')

            # Quota-safe evidence strategy:
            # 1) predictions is the highest-value probability endpoint.
            # 2) If it already supplies both predicted goals, stop immediately.
            # 3) Only then fall back to the broader evidence set.
            endpoint_diagnostics = {}
            try:
                d2 = self.http.get('/predictions', {'fixture': fid})
                out['predictions'] = d2
                response = d2.get('response') if isinstance(d2, dict) else None
                endpoint_diagnostics['predictions'] = {
                    'response_count': len(response) if isinstance(response, list) else (1 if isinstance(response, dict) else 0),
                    'errors': d2.get('errors') or [] if isinstance(d2, dict) else [],
                }
                pred = response[0] if isinstance(response, list) and response else None
                goals = pred.get('goals') if isinstance(pred, dict) else None
                if isinstance(goals, dict) and goals.get('home') is not None and goals.get('away') is not None:
                    out['endpoint_diagnostics'] = endpoint_diagnostics
                    out['rate_limit_diagnostics'] = dict(getattr(self.http, 'rate_limit_diagnostics', {}))
                    return out
            except Exception as ex:
                endpoint_diagnostics['predictions'] = {'response_count': 0, 'errors': [str(ex)[:160]]}

            for path,key in [('/fixtures/lineups','lineups'),('/injuries','injuries'),('/fixtures/statistics','statistics'),('/fixtures/headtohead','h2h')]:
                try:
                    if path=='/fixtures/lineups': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/injuries': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/fixtures/statistics': d2=self.http.get(path,{'fixture':fid})
                    elif path=='/fixtures/headtohead':
                        hi=best.get('teams',{}).get('home',{}).get('id'); ai=best.get('teams',{}).get('away',{}).get('id')
                        d2=self.http.get(path,{'h2h':f'{hi}-{ai}','last':10})
                    else: d2=self.http.get(path,{'fixture':fid})
                    out[key]=d2
                    if isinstance(d2,dict):
                        response = d2.get('response')
                        endpoint_diagnostics[key] = {
                            'response_count': len(response) if isinstance(response,list) else (1 if isinstance(response,dict) else 0),
                            'errors': d2.get('errors') or [],
                        }
                except Exception as ex:
                    endpoint_diagnostics[key] = {'response_count':0,'errors':[str(ex)[:160]]}
                    out.setdefault('errors',[]).append(str(ex)[:160])
            out['endpoint_diagnostics'] = endpoint_diagnostics

            if league_id and season and home_id and away_id:
                stats = {}
                for side, team_id in (('home', home_id), ('away', away_id)):
                    try:
                        ds = self.http.get('/teams/statistics', {
                            'league': league_id,
                            'season': season,
                            'team': team_id,
                        })
                        response = ds.get('response') if isinstance(ds,dict) else None
                        if isinstance(response,dict):
                            stats[side] = response
                    except Exception as ex:
                        out.setdefault('errors',[]).append(
                            f'team_statistics:{side}:{str(ex)[:120]}'
                        )
                if stats:
                    out['team_statistics'] = stats

            # Last-five fixture form is the second real-data fallback when
            # team-season statistics are unavailable (common for some cups,
            # youth and national-team competitions).
            recent = {}
            recent_diagnostics = {}
            for side, team_id in (('home', home_id), ('away', away_id)):
                if not team_id:
                    continue
                try:
                    dr = self.http.get('/fixtures', {'team': team_id, 'last': 5})
                    rows = dr.get('response', []) if isinstance(dr,dict) else []
                    recent_diagnostics[side] = {
                        'response_count': len(rows),
                        'errors': dr.get('errors') or [] if isinstance(dr,dict) else [],
                    }
                    gf=[]; ga=[]
                    for item in rows:
                        status = ((item.get('fixture') or {}).get('status') or {}).get('short')
                        if status not in {'FT','AET','PEN'}:
                            continue
                        goals = item.get('goals') or {}
                        gh, ga_ = goals.get('home'), goals.get('away')
                        if gh is None or ga_ is None:
                            continue
                        th = (item.get('teams') or {}).get('home',{}).get('id')
                        ta = (item.get('teams') or {}).get('away',{}).get('id')
                        if team_id == th:
                            gf.append(float(gh)); ga.append(float(ga_))
                        elif team_id == ta:
                            gf.append(float(ga_)); ga.append(float(gh))
                    if gf:
                        recent[side] = {
                            'goals_for_avg': sum(gf)/len(gf),
                            'goals_against_avg': sum(ga)/len(ga),
                            'sample_size': len(gf),
                        }
                except Exception as ex:
                    out.setdefault('errors',[]).append(
                        f'recent_fixtures:{side}:{str(ex)[:120]}'
                    )
            if recent:
                out['recent_team_form'] = recent
            out['recent_form_diagnostics'] = recent_diagnostics
            out['rate_limit_diagnostics'] = dict(getattr(self.http, 'rate_limit_diagnostics', {}))
        except Exception as ex:
            out['errors']=[str(ex)[:300]]
            out['rate_limit_diagnostics'] = dict(getattr(self.http, 'rate_limit_diagnostics', {}))
        return out

def flatten_provider_payload(raw:Dict[str,Any])->Dict[str,Any]:
    """Extract only evidence substantiated by a provider payload.
    Supports normalized direct fields and native API payloads.
    """
    out={}
    direct_keys=("home_xg","away_xg","home_attack","away_attack","home_defence","away_defence",
                 "form_home_prob","home_away_prob","h2h_home_prob","lineup_home_prob",
                 "injury_home_prob","suspension_home_prob","tactical_home_prob","elo_home_prob",
                 "ml_home_prob","home_advantage","dixon_coles_rho","evidence_quality",\n                 "home_goals_for_home_avg","home_goals_against_home_avg",\n                 "away_goals_for_away_avg","away_goals_against_away_avg",\n                 "home_recent_goals_for_avg","home_recent_goals_against_avg",\n                 "away_recent_goals_for_avg","away_recent_goals_against_avg")
    for k in direct_keys:
        if raw.get(k) is not None:
            try: out[k]=float(raw[k])
            except: pass
    pred=(raw.get('predictions') or {}).get('response',[]) if isinstance(raw.get('predictions'),dict) else []
    if pred:
        p=pred[0]
        goals=p.get('goals') or {}
        if isinstance(goals,dict):
            for side in ('home','away'):
                value=goals.get(side)
                try:
                    if value is not None:
                        out[f'{side}_predicted_goals']=float(value)
                except (TypeError,ValueError):
                    pass
        pct=p.get('percent') or {}
        if pct.get('home') is not None:
            try: out['ml_home_prob']=float(pct['home'])/100
            except: pass
        comp=p.get('comparison') or {}
        # API-Football prediction comparison can contain attack/defence percentages.
        def pct(value):
            try: return float(str(value).replace('%','').strip()) / 100.0
            except Exception: return None
        try:
            atk=comp.get('att') or {}
            ah,aa=pct(atk.get('home')),pct(atk.get('away'))
            if ah is not None and aa is not None:
                out['home_attack']=ah; out['away_attack']=aa
        except Exception: pass
        try:
            de=comp.get('def') or {}
            dh,da=pct(de.get('home')),pct(de.get('away'))
            if dh is not None and da is not None:
                out['home_defence']=dh; out['away_defence']=da
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

    # API-Football team-season statistics are a real-data fallback when
    # provider xG is unavailable. Keep the raw rate fields separate so the
    # probability engine can combine home scoring with opponent concession
    # without pretending these rates are xG.
    team_stats = raw.get('team_statistics') or {}
    if isinstance(team_stats,dict):
        home_stats = team_stats.get('home') or {}
        away_stats = team_stats.get('away') or {}
        def avg_goals(block, side):
            goals = block.get('goals') if isinstance(block,dict) else None
            if not isinstance(goals,dict):
                return None
            bucket = goals.get(side) or {}
            if not isinstance(bucket,dict):
                return None
            avg = bucket.get('average')
            try:
                return float(avg) if avg is not None else None
            except (TypeError, ValueError):
                return None

        out['home_goals_for_home_avg'] = avg_goals(home_stats, 'for')
        out['home_goals_against_home_avg'] = avg_goals(home_stats, 'against')
        out['away_goals_for_away_avg'] = avg_goals(away_stats, 'for')
        out['away_goals_against_away_avg'] = avg_goals(away_stats, 'against')

    recent = raw.get('recent_team_form') or {}
    if isinstance(recent,dict):
        h = recent.get('home') or {}
        a = recent.get('away') or {}
        if isinstance(h,dict):
            out['home_recent_goals_for_avg'] = h.get('goals_for_avg')
            out['home_recent_goals_against_avg'] = h.get('goals_against_avg')
        if isinstance(a,dict):
            out['away_recent_goals_for_avg'] = a.get('goals_for_avg')
            out['away_recent_goals_against_avg'] = a.get('goals_against_avg')

    # Remove unavailable placeholders rather than converting them to zero.
    out = {k:v for k,v in out.items() if v is not None}
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
