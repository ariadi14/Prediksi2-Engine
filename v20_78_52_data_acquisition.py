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


class FootballDataFixtureCSV:
    """Read-only CSV fallback for fixture identity and historical evidence.

    Supported common columns include football-data.co.uk fields
    Date, HomeTeam, AwayTeam, FTHG, FTAG, plus optional Time/Kickoff.
    The CSV is never treated as a live source. A row must actually match
    both teams and the requested local date before it can resolve a fixture.
    """
    name = "football-data-csv"

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("FOOTBALL_DATA_CSV_PATH", "data/football_data.csv")
        self._rows_cache = None
        self._last_fixture_lookup: Dict[str, Any] = {}

    @staticmethod
    def _norm(value: Any) -> str:
        import re, unicodedata
        x = unicodedata.normalize("NFKD", str(value or ""))
        x = "".join(ch for ch in x if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]", "", x.lower())

    @staticmethod
    def _date(value: Any) -> str:
        from datetime import datetime
        s = str(value or "").strip()
        if not s:
            return ""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s[:10], fmt).date().isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return s[:10]

    def _rows(self) -> List[Dict[str, str]]:
        if self._rows_cache is not None:
            return self._rows_cache
        if not self.available():
            self._rows_cache = []
            return self._rows_cache
        with open(self.path, "r", encoding="utf-8-sig", newline="") as f:
            self._rows_cache = [dict(row) for row in csv.DictReader(f)]
        return self._rows_cache

    def _row_date(self, row: Dict[str, str]) -> str:
        for key in ("Date", "date", "match_date", "MatchDate"):
            if row.get(key):
                return self._date(row.get(key))
        return ""

    def _team(self, row: Dict[str, str], home: bool) -> str:
        keys = ("HomeTeam", "home_team", "home", "Home") if home else ("AwayTeam", "away_team", "away", "Away")
        return next((str(row.get(k) or "").strip() for k in keys if row.get(k)), "")

    def _kickoff(self, row: Dict[str, str], date: str) -> str:
        raw = next((str(row.get(k) or "").strip() for k in
                    ("Time", "time", "Kickoff", "kickoff", "kickoff_local", "kickoff_wib")
                    if row.get(k)), "")
        if not raw:
            return ""
        if "T" in raw:
            return raw
        return f"{date}T{raw[:5]}:00+0700" if len(raw) >= 4 and ":" in raw[:5] else ""

    def available(self) -> bool:
        return os.path.isfile(self.path)

    def find_fixture(self, fixture: Dict[str, Any]) -> List[Dict[str, Any]]:
        home = fixture.get("home_canonical") or fixture.get("home")
        away = fixture.get("away_canonical") or fixture.get("away")
        date = str(fixture.get("match_date") or "")
        if not home or not away or not date or not self.available():
            self._last_fixture_lookup = {
                "path": self.path, "available": self.available(), "candidate_count": 0,
                "reason": "CSV_UNAVAILABLE_OR_MISSING_INPUT"
            }
            return []

        hn, an = self._norm(home), self._norm(away)
        candidates = []
        from rapidfuzz import fuzz
        for row in self._rows():
            if self._row_date(row) != date:
                continue
            rh, ra = self._team(row, True), self._team(row, False)
            hs = max(fuzz.ratio(hn, self._norm(rh)), fuzz.WRatio(hn, self._norm(rh)))
            aws = max(fuzz.ratio(an, self._norm(ra)), fuzz.WRatio(an, self._norm(ra)))
            if hs >= 82 and aws >= 82:
                kickoff = self._kickoff(row, date)
                if not kickoff:
                    # A football-data results CSV without kickoff time is not
                    # sufficient for the manual time-window filter.
                    continue
                candidates.append({
                    "fixture_id": f"csv:{date}:{self._norm(rh)}:{self._norm(ra)}",
                    "home_name": rh, "away_name": ra,
                    "date": date, "kickoff_utc": kickoff,
                    "kickoff_wib": kickoff, "competition": row.get("Div") or row.get("Competition"),
                    "home_score": round(float(hs), 1), "away_score": round(float(aws), 1),
                    "match_mode": "CSV_EXACT_DATE_TEAMS",
                    "csv_row": row,
                })
        self._last_fixture_lookup = {
            "path": self.path, "available": True, "date": date,
            "candidate_count": len(candidates),
            "source": "LOCAL_CSV",
        }
        return candidates[:1]

    def fetch(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        # Historical CSV is evidence only when the row exists; no values are
        # invented for missing fields. We calculate only explicit averages
        # from rows strictly before the target date.
        home = fixture.get("home_canonical") or fixture.get("home")
        away = fixture.get("away_canonical") or fixture.get("away")
        target_date = str(fixture.get("match_date") or "")
        if not home or not away or not target_date or not self.available():
            return {}
        rows = self._rows()
        if not rows:
            return {}

        hn, an = self._norm(home), self._norm(away)
        target = self._date(target_date)
        home_hist, away_hist = [], []
        for row in rows:
            d = self._row_date(row)
            if not d or d >= target:
                continue
            rh, ra = self._team(row, True), self._team(row, False)
            try:
                hg, ag = row.get("FTHG"), row.get("FTAG")
                if hg in (None, "") or ag in (None, ""):
                    continue
                hg, ag = float(hg), float(ag)
            except (TypeError, ValueError):
                continue
            if self._norm(rh) == hn:
                home_hist.append((d, hg, ag, True))
            elif self._norm(ra) == hn:
                home_hist.append((d, ag, hg, False))
            if self._norm(rh) == an:
                away_hist.append((d, hg, ag, True))
            elif self._norm(ra) == an:
                away_hist.append((d, ag, hg, False))

        home_hist = sorted(home_hist, reverse=True)[:20]
        away_hist = sorted(away_hist, reverse=True)[:20]
        if len(home_hist) < 1 or len(away_hist) < 1:
            return {}

        import statistics
        home_for = statistics.mean(x[1] for x in home_hist)
        home_against = statistics.mean(x[2] for x in home_hist)
        away_for = statistics.mean(x[1] for x in away_hist)
        away_against = statistics.mean(x[2] for x in away_hist)
        return {
            "fixture_match": {"id": fixture.get("fixture_id"), "homeTeam": {"name": home}, "awayTeam": {"name": away}},
            "home_goals_for_home_avg": home_for,
            "home_goals_against_home_avg": home_against,
            "away_goals_for_away_avg": away_for,
            "away_goals_against_away_avg": away_against,
            "historical_csv_source": self.path,
            "historical_home_matches_used": len(home_hist),
            "historical_away_matches_used": len(away_hist),
        }


class LocalFootballDatabase:
    """Read-only SQLite evidence provider built by v20_79_local_database.py.

    It supplies historical team evidence only. Fixture resolution remains
    authoritative through API-Football or a future fixture-schedule table.
    """
    name = "football-local-db"

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("FOOTBALL_DATABASE_PATH", "data/database/football.db")

    def available(self) -> bool:
        return os.path.isfile(self.path)

    @staticmethod
    def _norm(value: Any) -> str:
        import re, unicodedata
        x = unicodedata.normalize("NFKD", str(value or ""))
        x = "".join(ch for ch in x if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]", "", x.lower())

    def fetch(self, fixture: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available():
            return {}
        home = fixture.get("home_canonical") or fixture.get("home")
        away = fixture.get("away_canonical") or fixture.get("away")
        target = str(fixture.get("match_date") or "")
        if not home or not away or not target:
            return {}
        hn, an = self._norm(home), self._norm(away)
        conn = sqlite3.connect(self.path)
        try:
            def team_rows(team_norm: str, home_only: bool):
                col = "home_team_norm" if home_only else "away_team_norm"
                return conn.execute(
                    f"""SELECT match_date,home_goals,away_goals
                        FROM matches
                        WHERE {col}=? AND match_date < ?
                          AND home_goals IS NOT NULL AND away_goals IS NOT NULL
                        ORDER BY match_date DESC LIMIT 20""",
                    (team_norm, target),
                ).fetchall()
            hrows = team_rows(hn, True)
            arows = team_rows(an, False)
            if not hrows or not arows:
                return {}
            import statistics
            return {
                "fixture_match": {"id": fixture.get("fixture_id"),
                                  "homeTeam": {"name": home},
                                  "awayTeam": {"name": away}},
                "home_goals_for_home_avg": statistics.mean(r[1] for r in hrows),
                "home_goals_against_home_avg": statistics.mean(r[2] for r in hrows),
                "away_goals_for_away_avg": statistics.mean(r[2] for r in arows),
                "away_goals_against_away_avg": statistics.mean(r[1] for r in arows),
                "historical_db_source": self.path,
                "historical_home_matches_used": len(hrows),
                "historical_away_matches_used": len(arows),
            }
        finally:
            conn.close()
