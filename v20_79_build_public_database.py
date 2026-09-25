#!/usr/bin/env python3
"""Build the V20.79 historical database from current public datasets.

Sources are downloaded at build time; the resulting SQLite database is local
to the workflow run. OpenFootball is CC0/public-domain. Optional local CSV/ZIP
imports under data/imports are also included when present.
"""
from __future__ import annotations
import argparse
import shutil
import urllib.request
from pathlib import Path

from v20_79_local_database import build

SOURCES = {
    "openfootball-europe.zip": "https://github.com/openfootball/europe/archive/refs/heads/master.zip",
    "openfootball-world.zip": "https://github.com/openfootball/world/archive/refs/heads/master.zip",
    "openfootball-south-america.zip": "https://github.com/openfootball/south-america/archive/refs/heads/master.zip",
}

def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Prediksi2-V20.79-database-builder"})
    with urllib.request.urlopen(req, timeout=120) as src, dest.open("wb") as out:
        shutil.copyfileobj(src, out)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/database/football.db")
    ap.add_argument("--download-dir", default="data/raw/openfootball")
    args = ap.parse_args()

    dl = Path(args.download_dir)
    dl.mkdir(parents=True, exist_ok=True)
    inputs = []
    for name, url in SOURCES.items():
        dest = dl / name
        download(url, dest)
        inputs.append(dest)

    imports = Path("data/imports")
    if imports.exists():
        inputs.extend(sorted(p for p in imports.rglob("*") if p.suffix.lower() in {".csv", ".zip"}))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = build(out, inputs)
    print("V20.79 DATABASE BUILD:", stats)
    print("DATABASE:", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
