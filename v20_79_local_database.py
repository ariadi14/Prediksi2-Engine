#!/usr/bin/env python3
"""V20.79 local football database builder.

Builds a deduplicated SQLite database from local Football-Data CSV files and
OpenFootball CSV/TXT archives. Raw source files stay external; this module
normalizes them into one auditable schema and never invents match data.
"""
from __future__ import annotations
import argparse, csv, io, re, sqlite3, unicodedata, zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
 id INTEGER PRIMARY KEY,
 match_date TEXT NOT NULL,
 kickoff TEXT,
 country TEXT,
 competition TEXT,
 home_team TEXT NOT NULL,
 away_team TEXT NOT NULL,
 home_goals INTEGER,
 away_goals INTEGER,
 home_team_norm TEXT NOT NULL,
 away_team_norm TEXT NOT NULL,
 source TEXT NOT NULL,
 source_path TEXT NOT NULL,
 source_updated_at TEXT,
 dedup_key TEXT NOT NULL UNIQUE
);

"""

def norm(value: str) -> str:
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def date_iso(value: str, default_year: int | None = None) -> str:
    s = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%a %b %d %Y", "%a %b %d"):
        try:
            d = datetime.strptime(s, fmt)
            if fmt == "%a %b %d" and default_year:
                d = d.replace(year=default_year)
            return d.date().isoformat()
        except ValueError:
            pass
    # OpenFootball date strings can contain weekday/annotations.
    m = re.search(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})", s)
    if m:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date().isoformat()
    return ""

def parse_score(value: str):
    m = re.match(r"\s*(\d+)\s*[-–]\s*(\d+)", str(value or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

def season_year(path: str) -> int | None:
    m = re.search(r"(?:19|20)(\d{2})[-/](?:\d{2}|(?:19|20)\d{2})", path)
    return int(m.group(0)[:4]) if m else None

def csv_records(text: str, source: str, path: str) -> Iterable[dict]:
    rows = csv.DictReader(io.StringIO(text))
    for r in rows:
        home = (r.get("HomeTeam") or r.get("Team 1") or r.get("Home") or "").strip()
        away = (r.get("AwayTeam") or r.get("Team 2") or r.get("Away") or "").strip()
        if not home or not away:
            continue
        raw_date = r.get("Date") or ""
        d = date_iso(raw_date, season_year(path))
        if not d:
            continue
        hg, ag = parse_score(r.get("FT") or "")
        if hg is None:
            try:
                hg = int(float(r["FTHG"])) if r.get("FTHG") not in (None, "") else None
                ag = int(float(r["FTAG"])) if r.get("FTAG") not in (None, "") else None
            except (ValueError, TypeError):
                hg = ag = None
        kickoff = (r.get("Time") or r.get("Kickoff") or "").strip()
        competition = (r.get("Competition") or r.get("Div") or Path(path).stem).strip()
        yield {"date": d, "kickoff": kickoff, "competition": competition,
               "home": home, "away": away, "hg": hg, "ag": ag,
               "source": source, "path": path}

def openfootball_txt_records(text: str, source: str, path: str) -> Iterable[dict]:
    competition = ""
    country = Path(path).parts[-2] if len(Path(path).parts) >= 2 else ""
    current_date = ""
    year = season_year(path)
    m = re.search(r"^=\s*(.+)$", text, re.M)
    if m:
        competition = m.group(1).strip()
    date_re = re.compile(r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
    match_re = re.compile(r"^\s*(\d{1,2}:\d{2})\s+(.+?)\s+v\s+(.+?)\s+(\d+)[-–](\d+)")
    for line in text.splitlines():
        md = date_re.match(line)
        if md:
            y = int(md.group(3)) if md.group(3) else year
            if y:
                current_date = datetime.strptime(f"{md.group(1)} {md.group(2)} {y}", "%b %d %Y").date().isoformat()
            continue
        mm = match_re.match(line)
        if not mm or not current_date:
            continue
        yield {"date": current_date, "kickoff": mm.group(1), "competition": competition,
               "country": country, "home": mm.group(2).strip(), "away": mm.group(3).strip(),
               "hg": int(mm.group(4)), "ag": int(mm.group(5)), "source": source, "path": path}

def iter_zip(path: Path):
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith("/") or not name.lower().endswith((".csv", ".txt")):
                continue
            try:
                text = z.read(name).decode("utf-8-sig", "replace")
            except Exception:
                continue
            if name.lower().endswith(".txt"):
                yield from openfootball_txt_records(text, path.stem, name)
            else:
                yield from csv_records(text, path.stem, name)

def iter_path(path: Path):
    if path.suffix.lower() == ".zip":
        yield from iter_zip(path)
    elif path.suffix.lower() == ".csv":
        yield from csv_records(path.read_text(encoding="utf-8-sig", errors="replace"), "football-data", str(path))

def dedup_key(r: dict) -> str:
    # Do not include kickoff: different sources often encode timezone/rounding
    # differently. Competition remains part of identity so same teams/date in
    # separate competitions are not collapsed.
    return "|".join([r["date"], norm(r.get("competition","")), norm(r["home"]), norm(r["away"])])

def build(output: Path, inputs: list[Path]):
    conn = sqlite3.connect(output)
    conn.executescript(SCHEMA)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_teams_date ON matches(match_date,home_team_norm,away_team_norm)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_home_date ON matches(home_team_norm,match_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_away_date ON matches(away_team_norm,match_date)")
    seen = set()
    stats = {"read": 0, "inserted": 0, "duplicates": 0, "invalid": 0}
    for p in inputs:
        for r in iter_path(p):
            stats["read"] += 1
            if not r.get("date") or not r.get("home") or not r.get("away"):
                stats["invalid"] += 1
                continue
            k = dedup_key(r)
            if k in seen:
                stats["duplicates"] += 1
                continue
            # Existing DB rows are also protected by the UNIQUE constraint.
            try:
                conn.execute("""INSERT INTO matches
                    (match_date,kickoff,country,competition,home_team,away_team,
                     home_goals,away_goals,home_team_norm,away_team_norm,source,source_path,dedup_key)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r["date"],r.get("kickoff"),r.get("country",""),r["competition"],
                     r["home"],r["away"],r.get("hg"),r.get("ag"),norm(r["home"]),
                     norm(r["away"]),r["source"],r["path"],k))
                seen.add(k); stats["inserted"] += 1
            except sqlite3.IntegrityError:
                stats["duplicates"] += 1
    conn.commit()
    conn.close()
    return stats

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/database/football.db")
    ap.add_argument("inputs", nargs="+", help="ZIP/CSV source files")
    a = ap.parse_args()
    print(build(Path(a.output), [Path(x) for x in a.inputs]))
