"""V20.78.52 competition resolver.

Normalizes competition identity before provider routing. Generic names are not
silently mapped to a country-specific competition; country/ID metadata wins.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class CompetitionProfile:
    name: str
    normalized: str
    competition_type: str
    country: Optional[str]
    gender: str
    age_group: str
    competition_id: Optional[str] = None
    confidence: str = "MEDIUM"
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

def norm(v: str|None) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (v or "").lower()).split())

def resolve_competition(name: str|None, *, country: str|None=None, competition_id: str|int|None=None, gender: str|None=None, age_group: str|None=None) -> CompetitionProfile:
    n=norm(name); c=norm(country)
    if any(x in n for x in ("world cup", "euro", "copa america", "nations league", "world championship")):
        typ="INTERNATIONAL"
    elif any(x in n for x in ("qualifier", "qualification", "qualifying")):
        typ="QUALIFIER"
    elif any(x in n for x in ("friendly", "friendlies")):
        typ="FRIENDLY"
    elif any(x in n for x in ("cup", "copa", "fa cup", "knockout")):
        typ="CUP"
    elif any(x in n for x in ("women", "feminino", "femenino", "ladies")):
        typ="LEAGUE"
    elif n:
        typ="LEAGUE"
    else:
        typ="UNKNOWN"
    g=(gender or ("WOMEN" if any(x in n for x in ("women","feminino","femenino","ladies")) else "MEN")).upper()
    a=(age_group or ("U21" if "u21" in n or "under 21" in n else "U23" if "u23" in n or "under 23" in n else "YOUTH" if re.search(r"u1[6789]|u20|youth",n) else "SENIOR")).upper()
    confidence="HIGH" if competition_id is not None else ("HIGH" if name and country else "MEDIUM" if name else "LOW")
    return CompetitionProfile(name=name or "", normalized=n, competition_type=typ, country=country, gender=g, age_group=a, competition_id=str(competition_id) if competition_id is not None else None, confidence=confidence)
