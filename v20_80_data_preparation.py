"""V20.80 data-preparation layer.

Conservative preparation only: normalize, time-decay, shrink sparse historical
samples, and expose diagnostics. It never invents missing football data.
"""
from __future__ import annotations
from datetime import date, datetime
from math import exp
from typing import Any, Dict, Iterable, List, Optional


def _float(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_competition(value: Any) -> str:
    return " ".join(str(value or "").strip().upper().split())


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    s = str(value)[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def time_decay_weight(match_date: Any, reference_date: Any, half_life_days: float = 180.0) -> float:
    d = parse_date(match_date)
    r = parse_date(reference_date)
    if not d or not r:
        return 1.0
    age = max(0, (r - d).days)
    return exp(-0.69314718056 * age / max(1.0, float(half_life_days)))


def shrink_mean(values: Iterable[float], prior: float, strength: float = 5.0):
    xs = [float(x) for x in values if _float(x) is not None]
    if not xs:
        return None
    n = len(xs)
    return (sum(xs) + float(prior) * strength) / (n + strength)


def weighted_mean(values: Iterable[tuple[float, float]]):
    rows = [(float(v), max(0.0, float(w))) for v, w in values]
    den = sum(w for _, w in rows)
    return sum(v*w for v, w in rows) / den if den else None


def prepare_history(history_rows: List[Dict[str, Any]], reference_date: Any,
                    half_life_days: float = 180.0) -> Dict[str, Any]:
    rows = []
    for row in history_rows or []:
        d = parse_date(row.get("date") or row.get("match_date"))
        if not d:
            continue
        w = time_decay_weight(d, reference_date, half_life_days)
        rows.append({**row, "_v20_80_weight": w})
    return {"rows": rows, "usable_rows": len(rows), "half_life_days": half_life_days}


def _side_rate(rows, side, field):
    vals = []
    for r in rows:
        team = normalize_name(r.get(side))
        if not team:
            continue
        v = _float(r.get(field))
        if v is not None:
            vals.append((v, r.get("_v20_80_weight", 1.0)))
    return weighted_mean(vals)


def prepare_evidence(evidence: Dict[str, Any], fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare evidence without changing missing values into guesses."""
    e = dict(evidence or {})
    match_date = fixture.get("match_date")
    competition = fixture.get("competition")
    home = fixture.get("home_canonical") or fixture.get("home")
    away = fixture.get("away_canonical") or fixture.get("away")
    history = e.get("history_rows")
    prep = {
        "version": "V20.80",
        "home": normalize_name(home),
        "away": normalize_name(away),
        "competition": normalize_competition(competition),
        "reference_date": str(match_date or ""),
        "time_decay_half_life_days": 180.0,
        "history_rows_input": len(history) if isinstance(history, list) else 0,
        "history_rows_usable": 0,
        "shrinkage_applied": False,
        "opponent_adjustment_applied": False,
        "league_adjustment_applied": False,
    }
    if isinstance(history, list) and history:
        hp = prepare_history(history, match_date)
        prep["history_rows_usable"] = hp["usable_rows"]
        e["history_rows_prepared"] = hp["rows"]

        goals = []
        for r in hp["rows"]:
            hg = _float(r.get("home_goals"))
            ag = _float(r.get("away_goals"))
            if hg is not None: goals.append(hg)
            if ag is not None: goals.append(ag)
        league_mean = sum(goals) / len(goals) if goals else None

        if league_mean is not None:
            # Only fill a model field when the relevant team has actual rows.
            # Sparse rates are shrunk toward the observed league mean.
            home_for = _side_rate(hp["rows"], "home", "home_goals")
            away_for = _side_rate(hp["rows"], "away", "away_goals")
            if home_for is not None:
                e["v20_80_home_scoring_rate"] = shrink_mean([home_for], league_mean, 5.0)
                prep["shrinkage_applied"] = True
            if away_for is not None:
                e["v20_80_away_scoring_rate"] = shrink_mean([away_for], league_mean, 5.0)
                prep["shrinkage_applied"] = True

    # Existing provider values remain authoritative. This layer only records
    # normalized metadata when no structured history is available.
    e["v20_80_data_preparation"] = prep
    return e
