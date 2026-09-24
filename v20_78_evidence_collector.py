"""V20.78.1 Evidence Collector.

Provider-neutral evidence collection layer for V20.78.
- Accepts provider adapters (HTTP JSON or local deterministic adapters).
- Normalizes xG, form, home/away, H2H, attack/defence, Elo, lineup,
  injuries and suspensions into a common evidence contract.
- Never invents missing values.
- Preserves provenance and conflicts so the probability engine can weight them.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Protocol
import json, os
from urllib.request import Request, urlopen

EVIDENCE_FIELDS = [
    "home_xg", "away_xg", "home_attack", "away_attack",
    "home_defence", "away_defence", "form_home_prob", "home_away_prob",
    "h2h_home_prob", "lineup_home_prob", "injury_home_prob",
    "suspension_home_prob", "tactical_home_prob", "elo_home_prob",
    "ml_home_prob", "home_advantage", "dixon_coles_rho"
]

@dataclass
class EvidenceItem:
    field: str
    value: Any
    source: str
    confidence: float = 1.0
    timestamp: Optional[str] = None
    status: str = "OK"
    raw: Optional[Dict[str, Any]] = None

class EvidenceProvider(Protocol):
    name: str
    def fetch(self, fixture: Dict[str, Any]) -> Dict[str, Any]: ...

class StaticProvider:
    def __init__(self, name: str, payloads: Dict[str, Dict[str, Any]]):
        self.name, self.payloads = name, payloads
    def fetch(self, fixture):
        key=fixture.get("fixture_key") or "|".join(str(fixture.get(k,'')) for k in ("competition","home","away","match_date","kickoff"))
        return dict(self.payloads.get(key, {}))

class HTTPJSONProvider:
    """Simple configurable JSON provider. Endpoint must return a JSON object.
    Request is POSTed as the fixture object. Auth is supplied via env var token.
    """
    def __init__(self, name: str, endpoint: str, token_env: Optional[str]=None, timeout: int=8):
        self.name, self.endpoint, self.token_env, self.timeout = name, endpoint, token_env, timeout
    def fetch(self, fixture):
        body=json.dumps(fixture).encode()
        headers={"Content-Type":"application/json","Accept":"application/json"}
        if self.token_env and os.getenv(self.token_env): headers["Authorization"]="Bearer "+os.getenv(self.token_env)
        req=Request(self.endpoint,data=body,headers=headers,method="POST")
        with urlopen(req,timeout=self.timeout) as r:
            data=json.loads(r.read().decode("utf-8"))
        return data if isinstance(data,dict) else {}

class EvidenceCollector:
    VERSION="V20.78.1"
    def __init__(self, providers: Optional[List[EvidenceProvider]]=None):
        self.providers=providers or []

    @staticmethod
    def _prob(v):
        if v is None:return None
        try:
            x=float(v)
            # Accept either 0..1 or 0..100 percentage input.
            if 1 < x <= 100:x/=100.0
            return x if 0<=x<=1 else None
        except:return None

    def collect(self, fixture: Dict[str,Any]) -> Dict[str,Any]:
        merged: Dict[str,Any]={}
        provenance: Dict[str,List[Dict[str,Any]]]={}
        errors=[]
        for provider in self.providers:
            try: payload=provider.fetch(fixture) or {}
            except Exception as ex:
                errors.append({"source":provider.name,"error":str(ex)[:300]}); continue
            for field in EVIDENCE_FIELDS:
                if field not in payload: continue
                val=payload[field]
                if field.endswith("_prob"):
                    val=self._prob(val)
                if val is None: continue
                item={"source":provider.name,"value":val,"confidence":float(payload.get(f"{field}_confidence",1.0))}
                provenance.setdefault(field,[]).append(item)
                if field not in merged: merged[field]=val
        # Resolve multiple sources using confidence-weighted mean for numeric fields.
        conflicts=[]
        for field, items in provenance.items():
            nums=[]
            for it in items:
                try: nums.append((float(it["value"]),max(0.0,float(it["confidence"]))))
                except: pass
            if not nums: continue
            if len(nums)==1: merged[field]=nums[0][0]
            else:
                den=sum(w for _,w in nums) or 1.0
                merged[field]=sum(v*w for v,w in nums)/den
                spread=max(v for v,_ in nums)-min(v for v,_ in nums)
                if spread > 0.20 and field.endswith("_prob"):
                    conflicts.append({"field":field,"spread":spread,"sources":[x["source"] for x in items]})
        merged["evidence_provenance"]=provenance
        merged["evidence_sources"]=sorted({x["source"] for xs in provenance.values() for x in xs})
        merged["evidence_status"]="CONFLICT" if conflicts else ("VERIFIED" if len(merged["evidence_sources"])>=2 else ("SINGLE_SOURCE" if merged["evidence_sources"] else "MISSING"))
        merged["evidence_conflicts"]=conflicts
        merged["collector_errors"]=errors
        return merged

    def collect_many(self, fixtures: List[Dict[str,Any]]) -> Dict[str,Dict[str,Any]]:
        out={}
        for f in fixtures:
            key=f.get("fixture_key") or "|".join(str(f.get(k,'')) for k in ("competition","home","away","match_date","kickoff"))
            out[key]=self.collect({**f,"fixture_key":key})
        return out
