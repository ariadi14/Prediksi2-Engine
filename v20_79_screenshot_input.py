#!/usr/bin/env python3
"""V20.79 single source of truth for workflow screenshot input."""
from __future__ import annotations
import argparse, os
from pathlib import Path
from typing import List
from PIL import Image

LABELS = {"screenshot", "screenshot paths", "screenshot_path", "screenshot_paths"}

def normalize_raw(raw: str) -> List[str]:
    value = str(raw or "").strip()
    if ":" in value:
        prefix, candidate = value.split(":", 1)
        if prefix.strip().lower() in LABELS:
            value = candidate.strip()
    return [x.strip().strip('"').strip("'") for x in value.split(",") if x.strip()]

def resolve_one(value: str) -> Path:
    direct = Path(value)
    if direct.is_file():
        return direct
    name = direct.name
    matches = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".git"]
        if name in files:
            matches.append(Path(root) / name)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit("SCREENSHOT_AMBIGUOUS: " + value + " -> " + ", ".join(map(str, matches)))
    raise SystemExit(
        "SCREENSHOT_NOT_FOUND: " + value +
        ". File harus benar-benar ada di repository runner; "
        "file dari galeri HP/chat tidak otomatis tersedia di GitHub Actions."
    )

def validate(path: Path) -> Path:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.width <= 0 or image.height <= 0:
                raise ValueError("invalid image size")
            print("SCREENSHOT:", path)
            print("  FORMAT:", image.format)
            print("  SIZE:", image.size)
            print("  MODE:", image.mode)
    except Exception as exc:
        raise SystemExit(f"SCREENSHOT_INVALID: {path}: {exc}") from exc
    return path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    raw_paths = normalize_raw(args.raw)
    if not raw_paths:
        raise SystemExit("SCREENSHOT_INPUT_EMPTY: screenshot_paths kosong.")
    resolved = [validate(resolve_one(x)) for x in raw_paths]
    unique = list(dict.fromkeys(str(x) for x in resolved))
    Path(args.output).write_text("\n".join(unique) + "\n", encoding="utf-8")
    print(f"BATCH SCREENSHOT VALIDATION: PASS ({len(unique)} files)")
    print("NORMALIZED SCREENSHOT PATHS:")
    for x in unique:
        print("  ", x)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
