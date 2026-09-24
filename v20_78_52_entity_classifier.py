"""V20.78.52 entity/competition classification.

Separates club fixtures from national teams and age/gender variants so that
provider routing and evidence collection never mix incompatible team data.
Market/line data is deliberately outside this module; it remains screenshot-only.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import re


@dataclass(frozen=True)
class EntityProfile:
    name: str
    entity_type: str          # CLUB / NATIONAL
    gender: str               # MEN / WOMEN / UNKNOWN
    age_group: str            # SENIOR / U23 / U21 / YOUTH / UNKNOWN
    country: Optional[str] = None
    confidence: str = "MEDIUM"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Explicit markers only. Avoid treating an arbitrary club containing "U21" as
# a national team unless the name/competition provides enough evidence.
WOMEN_MARKERS = (" women", " womens", " women's", " ladies", " femenino", " feminina", " feminino", "wnt")
AGE_MARKERS = {
    "U21": ("u21", "under 21", "under-21"),
    "U23": ("u23", "under 23", "under-23"),
    "YOUTH": ("u20", "u19", "u18", "u17", "u16", "youth", "juvenile"),
}

# Countries/territories are used only as a supporting signal. This list is not
# intended as a complete FIFA membership database.
COUNTRIES = {
    "argentina", "australia", "austria", "belgium", "brazil", "brasil",
    "canada", "chile", "china", "colombia", "croatia", "denmark",
    "ecuador", "england", "finland", "france", "germany", "ghana",
    "greece", "india", "indonesia", "iran", "ireland", "italy", "japan",
    "korea", "korea republic", "malaysia", "mexico", "morocco", "netherlands",
    "new zealand", "nigeria", "norway", "paraguay", "peru", "poland",
    "portugal", "scotland", "senegal", "serbia", "singapore", "slovakia",
    "slovenia", "south africa", "spain", "sweden", "switzerland", "thailand",
    "tunisia", "turkey", "ukraine", "united states", "uruguay", "venezuela",
    "vietnam", "wales", "zambia",
}


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _age_group(name: str, competition: str) -> str:
    text = f"{name} {competition}"
    for group, markers in AGE_MARKERS.items():
        if any(m in text for m in markers):
            return group
    return "SENIOR"


def _gender(name: str, competition: str) -> str:
    text = f" {name} {competition} "
    if any(m in text for m in WOMEN_MARKERS):
        return "WOMEN"
    return "MEN"


def _country_base(name: str) -> str:
    n = normalize_name(name)
    n = re.sub(r"\b(under[- ]?\d+|u\d+)\b", "", n)
    n = re.sub(r"\b(women|womens|women\'s|ladies)\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def looks_like_national_team(name: str, competition: str = "") -> bool:
    n = normalize_name(name)
    base = _country_base(name)
    c = normalize_name(competition)
    if any(marker in c for marker in ("world cup", "euro", "copa america", "nations league", "world championship", "qualifier", "qualification", "international")):
        # Competition alone is only a supporting signal; both entity names are
        # checked by the caller. This function remains conservative.
        pass
    if n in COUNTRIES or base in COUNTRIES:
        return True
    if n.startswith("team ") or n.endswith(" national team"):
        return True
    return False


def classify_entity(name: str, competition: str = "", *, explicit_type: Optional[str] = None,
                     country: Optional[str] = None) -> EntityProfile:
    n = normalize_name(name)
    c = normalize_name(competition)
    age = _age_group(n, c)
    gender = _gender(n, c)

    if explicit_type:
        et = explicit_type.upper()
        if et in {"NATIONAL", "CLUB"}:
            return EntityProfile(name=name, entity_type=et, gender=gender,
                                 age_group=age, country=country, confidence="HIGH")

    national = looks_like_national_team(name, competition)
    # International competition markers increase confidence only when the name
    # itself looks national; they never turn a club into a country.
    conf = "HIGH" if national and _country_base(name) in COUNTRIES else "MEDIUM"
    return EntityProfile(name=name,
                         entity_type="NATIONAL" if national else "CLUB",
                         gender=gender, age_group=age, country=country if national else None,
                         confidence=conf)


def classify_fixture(home: str, away: str, competition: str = "", *,
                     home_type: Optional[str] = None, away_type: Optional[str] = None) -> Dict[str, Any]:
    h = classify_entity(home, competition, explicit_type=home_type)
    a = classify_entity(away, competition, explicit_type=away_type)
    same_entity_family = h.entity_type == a.entity_type and h.gender == a.gender and h.age_group == a.age_group

    if h.entity_type == "NATIONAL" and a.entity_type == "NATIONAL":
        fixture_type = "NATIONAL_VS_NATIONAL"
    elif h.entity_type == "CLUB" and a.entity_type == "CLUB":
        fixture_type = "CLUB_VS_CLUB"
    else:
        fixture_type = "MIXED_ENTITY"

    return {
        "home": h.to_dict(),
        "away": a.to_dict(),
        "fixture_type": fixture_type,
        "same_entity_family": same_entity_family,
        "data_isolation_key": f"{h.entity_type}:{h.gender}:{h.age_group}|{a.entity_type}:{a.gender}:{a.age_group}",
        "competition": competition,
    }
