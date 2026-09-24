"""V20.78.52 free-first data acquisition, quota manager and cache.
No fabricated data: exhausted providers fall back to fresh cache/next provider;
missing fields remain MISSING.
"""
from __future__ import annotations
import csv, json, os, sqlite3, time
from typing import Any, Dict, Iterable, List, Optional

class TTLCache:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT NOT NULL, ts REAL NOT NULL, ttl REAL NOT NULL)")
    def get(self, key: str, now: Optional[float] = None):
        now = time.time() if now is None else now
        row = self.conn.execute("SELECT v,ts,ttl FROM cache WHERE k=?", (key,)).fetchone()
        if not row: return None
        if now - row[1] > row[2]:
            self.conn.execute("DELETE FROM cache WHERE k=?", (key,)); self.conn.commit(); return None
        try: return json.loads(row[0])
        except Exception: return None
    def put(self, key: str, value: Any, ttl: float, now: Optional[float] = None):
        now = time.time() if now is None else now
        self.conn.execute("INSERT OR REPLACE INTO cache(k,v,ts,ttl) VALUES(?,?,?,?)", (key,json.dumps(value),now,float(ttl)))
        self.conn.commit()

DEFAULT_TTLS = {
    "fixture": 6*3600, "h2h": 24*3600, "form": 6*3600, "standings": 12*3600,
    "injury": 2*3600, "lineup": 20*60, "statistics": 6*3600, "xg": 6*3600,
}

class QuotaManager:
    def __init__(self, limits: Optional[Dict[str,int]]=None):
        self.limits = limits or {}
        self.used = {k:0 for k in self.limits}
    def remaining(self, provider: str) -> Optional[int]:
        if provider not in self.limits: return None
        return max(0, self.limits[provider]-self.used.get(provider,0))
    def can_request(self, provider: str) -> bool:
        r=self.remaining(provider); return True if r is None else r > 0
    def consume(self, provider: str, n: int=1) -> bool:
        if not self.can_request(provider): return False
        if provider in self.used: self.used[provider] += max(0,n)
        return True
    def status(self) -> Dict[str,Any]:
        return {p:{"limit":self.limits[p],"used":self.used.get(p,0),"remaining":self.remaining(p)} for p in self.limits}

class DataAcquisitionManager:
    """Provider-neutral orchestrator. Providers expose fetch(fixture).
    Optional provider.fetch_field(fixture, field) is supported for field-level fallback.
    """
    def __init__(self, providers: Iterable[Any], quota: Optional[QuotaManager]=None, cache: Optional[TTLCache]=None):
        self.providers=list(providers); self.quota=quota or QuotaManager(); self.cache=cache or TTLCache()
    def _key(self, fixture: Dict[str,Any], field: str) -> str:
        ident=fixture.get("fixture_id") or f"{fixture.get('home')}|{fixture.get('away')}|{fixture.get('match_date')}"
        return f"{ident}:{field}"
    def acquire(self, fixture: Dict[str,Any], fields: Optional[List[str]]=None) -> Dict[str,Any]:
        fields=fields or ["fixture","h2h","form","injury","lineup","statistics","xg","standings"]
        evidence={}; meta={}; provider_errors=[]
        for field in fields:
            key=self._key(fixture,field); cached=self.cache.get(key)
            if cached is not None:
                evidence[field]=cached; meta[field]={"source":"CACHE","status":"CACHED"}; continue
            found=False
            for p in self.providers:
                name=getattr(p,"name",p.__class__.__name__).lower()
                if not self.quota.can_request(name):
                    continue
                try:
                    if hasattr(p,"fetch_field"):
                        value=p.fetch_field(fixture,field)
                    else:
                        raw=p.fetch(fixture) or {}; value=raw.get(field)
                    self.quota.consume(name)
                    if value is not None and value != {} and value != []:
                        evidence[field]=value; meta[field]={"source":name,"status":"LIVE"};
                        self.cache.put(key,value,DEFAULT_TTLS.get(field,3600)); found=True; break
                except Exception as ex:
                    provider_errors.append({"provider":name,"field":field,"error":str(ex)[:200]})
            if not found:
                evidence.setdefault(field,None); meta[field]={"source":None,"status":"MISSING"}
        evidence["acquisition_meta"]=meta
        evidence["quota_status"]=self.quota.status()
        evidence["collector_errors"]=provider_errors
        evidence["data_status"]="AVAILABLE" if any(v is not None for k,v in evidence.items() if k not in {"acquisition_meta","quota_status","collector_errors"}) else "MISSING"
        return evidence

class FootballDataCSV:
    """Read-only historical CSV helper; no CSV is fabricated or downloaded."""
    def __init__(self, path: str): self.path=path
    def available(self)->bool: return os.path.isfile(self.path)
    def rows(self, limit: Optional[int]=None)->List[Dict[str,str]]:
        if not self.available(): return []
        with open(self.path,"r",encoding="utf-8-sig",newline="") as f:
            r=csv.DictReader(f); out=[]
            for row in r:
                out.append(dict(row))
                if limit and len(out)>=limit: break
            return out
