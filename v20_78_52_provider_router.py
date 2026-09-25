"""V20.78.52 provider router with entity-aware routing.

Rules:
- Sportmonks is used only for Danish Superliga and Scottish Premiership.
- National-team fixtures are routed through broad providers, never through
  club-only competition assumptions.
- API-Football is preferred for broad coverage; football-data is fallback.
- Missing data is not converted into negative evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from v20_78_52_entity_classifier import classify_fixture

SPORTMONKS_FREE_COMPETITIONS = {
    "danish superliga",
    "3f superliga",
    "scottish premiership",
}

SPORTMONKS_ALIASES = {
    "danish superliga": "Danish Superliga",
    "3f superliga": "Danish Superliga",
    "scottish premiership": "Scottish Premiership",
}


def normalize_competition(value: str | None) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


@dataclass(frozen=True)
class ProviderRoute:
    competition: str
    fixture_type: str
    primary: str
    fallback: List[str]
    reason: str


def route_provider(
    competition: str | None,
    *,
    home: Optional[str] = None,
    away: Optional[str] = None,
    home_type: Optional[str] = None,
    away_type: Optional[str] = None,
    api_football_available: bool = True,
    football_data_available: bool = True,
    sportmonks_available: bool = True,
) -> ProviderRoute:
    """Production route: API-Football first, local CSV second.

    Sportmonks and OpenFoot are intentionally excluded from V20.79 production
    routing. The CSV layer is a local/historical fallback only.
    """
    fixture_type = "UNKNOWN"
    if home is not None and away is not None:
        fixture_type = classify_fixture(
            home, away, competition or "",
            home_type=home_type, away_type=away_type
        )["fixture_type"]

    if api_football_available:
        fallback = ["football-data-csv"] if football_data_available else []
        return ProviderRoute(
            competition or "", fixture_type, "api-football", fallback,
            "api-football-live-primary"
        )

    if football_data_available:
        return ProviderRoute(
            competition or "", fixture_type, "football-data-csv", [],
            "api-football-unavailable-csv-fallback"
        )

    return ProviderRoute(
        competition or "", fixture_type, "missing", [],
        "no-api-football-and-no-csv"
    )
