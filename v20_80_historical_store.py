"""V20.80 historical match store.

SQLite-backed canonical store for monthly CSV imports. Imports are additive:
existing match_id rows are preserved, exact duplicates are ignored, and
missing optional fields never overwrite existing values.
"""
from __future__ import annotations

import csv
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    country TEXT,
    league TEXT,
    season TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    home_xg REAL,
    away_xg REAL,
    source TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team, away_team);
CREATE INDEX IF NOT EXISTS idx_matches_league_season ON matches(league, season);
"""

CANONICAL_COLUMNS = (
    "match_id","date","country","league","season","home_team","away_team",
    "home_goals","away_goals","home_xg","away_xg","source","imported_at"
)

ALIASES = {
    "date": ("date","Date","match_date","MatchDate"),
    "country": ("country","Country"),
    "league": ("league","League","Div","division"),
    "season": ("season","Season"),
    "home_team": ("home_team","HomeTeam","home","Home"),
    "away_team": ("away_team","AwayTeam","away","Away"),
    "home_goals": ("home_goals","FTHG","HG","HomeGoals"),
    "away_goals": ("away_goals","FTAG","AG","AwayGoals"),
    "home_xg": ("home_xg","HomeXG","home_xg_value","xGHome"),
    "away_xg": ("away_xg","AwayXG","away_xg_value","xGAway"),
    "match_id": ("match_id","MatchID","fixture_id","FixtureID","id"),
}

def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None

def _first(row: Dict[str, Any], names: Iterable[str]) -> Optional[str]:
    for name in names:
        if name in row:
            value = _clean(row[name])
            if value is not None:
                return value
    return None

def _number(value: Any, integer: bool = False):
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value)) if integer else float(value)
    except (TypeError, ValueError):
        return None

def make_match_id(row: Dict[str, Any]) -> str:
    explicit = _first(row, ALIASES["match_id"])
    if explicit:
        return explicit
    key = "|".join([
        _first(row, ALIASES["date"]) or "",
        _first(row, ALIASES["league"]) or "",
        _first(row, ALIASES["home_team"]) or "",
        _first(row, ALIASES["away_team"]) or "",
    ]).lower()
    return "derived-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]

def normalize_row(row: Dict[str, Any], source: str, imported_at: Optional[str] = None) -> Dict[str, Any]:
    date = _first(row, ALIASES["date"])
    home = _first(row, ALIASES["home_team"])
    away = _first(row, ALIASES["away_team"])
    if not date or not home or not away:
        raise ValueError("REQUIRED_FIELDS_MISSING: date, home_team, away_team")
    return {
        "match_id": make_match_id(row),
        "date": date,
        "country": _first(row, ALIASES["country"]),
        "league": _first(row, ALIASES["league"]),
        "season": _first(row, ALIASES["season"]),
        "home_team": home,
        "away_team": away,
        "home_goals": _number(_first(row, ALIASES["home_goals"]), True),
        "away_goals": _number(_first(row, ALIASES["away_goals"]), True),
        "home_xg": _number(_first(row, ALIASES["home_xg"])),
        "away_xg": _number(_first(row, ALIASES["away_xg"])),
        "source": source,
        "imported_at": imported_at or datetime.now(timezone.utc).isoformat(),
    }

class HistoricalMatchStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0])

    def import_csv(self, csv_path: str, source: Optional[str] = None) -> Dict[str, int]:
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(csv_path)
        source = source or os.path.basename(csv_path)
        inserted = updated = skipped = invalid = 0
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                try:
                    row = normalize_row(raw, source)
                except ValueError:
                    invalid += 1
                    continue
                existing = self.conn.execute(
                    "SELECT * FROM matches WHERE match_id=?", (row["match_id"],)
                ).fetchone()
                if existing is None:
                    cols = ", ".join(CANONICAL_COLUMNS)
                    marks = ", ".join("?" for _ in CANONICAL_COLUMNS)
                    self.conn.execute(
                        f"INSERT INTO matches ({cols}) VALUES ({marks})",
                        [row[c] for c in CANONICAL_COLUMNS],
                    )
                    inserted += 1
                else:
                    # Monthly updates may add xG/metadata later; never erase
                    # a value already present with a missing CSV value.
                    changed = False
                    for c in CANONICAL_COLUMNS:
                        if c in ("match_id","date","home_team","away_team","imported_at"):
                            continue
                        if row[c] is not None and existing[c] != row[c]:
                            self.conn.execute(
                                f"UPDATE matches SET {c}=? WHERE match_id=?",
                                (row[c], row["match_id"]),
                            )
                            changed = True
                    if changed:
                        self.conn.execute(
                            "UPDATE matches SET imported_at=? WHERE match_id=?",
                            (row["imported_at"], row["match_id"]),
                        )
                        updated += 1
                    else:
                        skipped += 1
        self.conn.commit()
        return {"inserted": inserted, "updated": updated, "skipped": skipped, "invalid": invalid}

    def recent(self, limit: int = 20):
        rows = self.conn.execute(
            "SELECT * FROM matches ORDER BY date DESC, match_id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
