#!/usr/bin/env python3
"""V20.79 real end-to-end Prediksi 2 pipeline.

No synthetic fixtures, hard-coded probabilities, invented markets, or forced
parlay quota are used in this pipeline. The screenshot is the source of truth
for visible market/line/odds; provider data is used only for fixture/evidence.
"""
from __future__ import annotations

import argparse, json, math
from pathlib import Path
from typing import Any, Dict, List

from fast_pelangi_parser import FastPelangiParser
from v20_78_39_provider_aware_pipeline import ProviderAwarePipeline
from v20_78_probability_engine import AdaptiveProbabilityEngine, score_matrix


def settlement_return(score_home: int, score_away: int, line: float, side: str, odds: float) -> float:
    """Gross return per 1 unit for one Asian line component."""
    diff = score_home - score_away if side.lower() == "home" else score_away - score_home
    v = diff + line
    if v > 0:
        return odds
    if v == 0:
        return 1.0
    return 0.0


def asian_ev(home_xg: float, away_xg: float, market: str, line: float,
             selection: str, odds: float, rho: float = -0.08) -> float:
    """Expected net return for exact Asian O/U or HDP line."""
    matrix = score_matrix(home_xg, away_xg, max_goals=12, rho=rho)
    m = str(market).upper()
    total = 0.0
    weight_sum = 0.0

    if m == "O/U":
        # Over/Under line is split into adjacent quarter components.
        if abs(line * 4 - round(line * 4)) > 1e-9:
            raise ValueError(f"Unsupported total line: {line}")
        q = round(line * 4) % 2
        if q == 0:
            components = [line]
        else:
            components = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
        for h, row in enumerate(matrix):
            for a, p in enumerate(row):
                s = h + a
                gross = 0.0
                for component in components:
                    win = s > component if selection.lower() == "over" else s < component
                    push = s == component
                    gross += odds if win else (1.0 if push else 0.0)
                gross /= len(components)
                total += p * gross
        return total - 1.0

    if m == "HDP":
        if abs(line * 4 - round(line * 4)) > 1e-9:
            raise ValueError(f"Unsupported handicap line: {line}")
        q = round(line * 4) % 2
        if q == 0:
            components = [line]
        else:
            components = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
        for h, row in enumerate(matrix):
            for a, p in enumerate(row):
                gross = sum(
                    settlement_return(h, a, c, selection, odds)
                    for c in components
                ) / len(components)
                total += p * gross
        return total - 1.0

    return None


def evaluate_markets(prediction: Dict[str, Any], visible: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    markets = prediction.get("markets", {})
    out = []
    for m in visible:
        market = str(m.get("market", "")).upper()
        selection = m.get("selection")
        line = m.get("line")
        odds = float(m.get("odds"))
        p = None
        if market == "1X2":
            p = markets.get("1X2", {}).get(selection)
        elif market in ("O/U", "HDP"):
            block = markets.get(market, {}).get(str(line), {})
            p = block.get(selection)

        if p is None:
            continue

        p = float(p)
        implied = 1.0 / odds if odds > 1 else None
        if market in ("O/U", "HDP") and prediction.get("home_xg") is not None and prediction.get("away_xg") is not None:
            ev = asian_ev(
                float(prediction["home_xg"]),
                float(prediction["away_xg"]),
                market, float(line), str(selection), odds,
                float(prediction.get("model_components", {}).get("dixon_coles_rho", -0.08)),
            )
        else:
            ev = p * odds - 1.0

        out.append({
            "market": market,
            "selection": selection,
            "line": line,
            "odds": odds,
            "model_probability": p,
            "implied_probability": implied,
            "edge": p - implied if implied is not None else None,
            "ev": ev,
            "source_market_locked": True,
        })
    return out


def in_window(hhmm: str, window: str) -> bool:
    h, m = map(int, hhmm[:5].split(':'))
    t = h * 60 + m
    starts = {"18:00-21:00": 1080, "21:00-00:00": 1260, "00:00-05:00": 0, "05:00-10:00": 300}
    ends = {"18:00-21:00": 1260, "21:00-00:00": 1440, "00:00-05:00": 300, "05:00-10:00": 600}
    a, b = starts[window], ends[window]
    return a <= t < b if a < b else (t >= a or t < b)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screenshot", nargs="+", required=True, help="One or more PelangiEuro screenshot paths")
    ap.add_argument("--time-window", required=True)
    ap.add_argument("--min-probability", type=float, default=0.55)
    ap.add_argument("--min-ev", type=float, default=0.02)
    ap.add_argument("--output", default="artifacts/v20_79_final_output.json")
    args = ap.parse_args()

    screenshots = [str(Path(x)) for x in args.screenshot]
    missing = [x for x in screenshots if not Path(x).is_file()]
    if missing:
        raise SystemExit(f"SCREENSHOT_NOT_FOUND: {missing}")

    allowed = {"18:00-21:00", "21:00-00:00", "00:00-05:00", "05:00-10:00"}
    if args.time_window not in allowed:
        raise SystemExit(f"INVALID_TIME_WINDOW: {args.time_window}")

    parser = FastPelangiParser()
    fixtures = []
    parsed_by_screenshot = []
    for screenshot in screenshots:
        parsed = parser.replay([screenshot], time_choice="ALL")
        parsed_fixtures = parsed.get("fixtures", [])
        parsed_by_screenshot.append({
            "screenshot": screenshot,
            "parsed_fixtures": len(parsed_fixtures),
        })
        for fixture in parsed_fixtures:
            fixture = dict(fixture)
            fixture["source_screenshot"] = screenshot
            fixtures.append(fixture)

    if not fixtures:
        raise SystemExit("NO_FIXTURES_PARSED_FROM_SCREENSHOTS")

    # Time filtering happens after provider resolution as a fallback because
    # older screenshots may not expose kickoff in the left crop.
    pipeline = ProviderAwarePipeline()
    results = []
    unresolved = []
    seen_fixture_keys = set()

    for fixture in fixtures:
        if not fixture.get("home") or not fixture.get("away"):
            unresolved.append({"fixture": fixture, "reason": "MISSING_TEAM_NAME"})
            continue

        resolved, validation = pipeline.resolve_fixture(fixture)
        if validation.get("status") != "VALID":
            unresolved.append({
                "fixture": fixture,
                "reason": validation.get("reason", "FIXTURE_REJECTED"),
                "validation": validation,
            })
            continue

        # Multiple screenshots may overlap at a page boundary. Deduplicate only
        # after real provider resolution so we do not accidentally collapse
        # different competitions or dates.
        resolved_key = "|".join(str(resolved.get(k, "")) for k in (
            "competition", "home_canonical", "away_canonical", "match_date", "kickoff"
        ))
        if resolved_key in seen_fixture_keys:
            continue
        seen_fixture_keys.add(resolved_key)

        resolved_kickoff = resolved.get("kickoff")
        if not resolved_kickoff:
            unresolved.append({"fixture": resolved, "reason": "KICKOFF_UNAVAILABLE_AFTER_RESOLUTION"})
            continue
        if not in_window(resolved_kickoff, args.time_window):
            continue

        provider_evidence = pipeline.ev.fetch(resolved)
        if provider_evidence.get("status") != "ENRICHED":
            unresolved.append({
                "fixture": resolved,
                "reason": provider_evidence.get("reason", "EVIDENCE_UNAVAILABLE"),
                "validation": validation,
            })
            continue

        visible = resolved.get("markets") or []
        # Ask the probability engine to calculate every exact line visible in
        # the screenshot, including quarter lines.
        ev_payload = dict(provider_evidence.get("payload") or {})
        ev_payload["ou_lines"] = sorted({
            float(x["line"]) for x in visible
            if str(x.get("market")).upper() == "O/U" and x.get("line") is not None
        })
        ev_payload["handicap_lines"] = sorted({
            float(x["line"]) for x in visible
            if str(x.get("market")).upper() == "HDP" and x.get("line") is not None
        })

        fixture_key = "|".join(
            str(resolved.get(k, "")) for k in
            ("competition", "home_canonical", "away_canonical", "match_date", "kickoff")
        )
        prediction = pipeline.prob.run(fixture_key, {"status": "ENRICHED", "payload": ev_payload}, visible)
        if prediction.get("status") != "CALCULATED":
            unresolved.append({
                "fixture": resolved,
                "reason": "PROBABILITY_INSUFFICIENT",
                "prediction": prediction,
            })
            continue

        evaluated = evaluate_markets(prediction, visible)
        for candidate in evaluated:
            candidate.update({
                "source_screenshot": resolved.get("source_screenshot") or fixture.get("source_screenshot"),
                "competition": resolved.get("competition"),
                "home": resolved.get("home_canonical") or resolved.get("home"),
                "away": resolved.get("away_canonical") or resolved.get("away"),
                "kickoff": resolved.get("kickoff"),
                "fixture_id": resolved.get("fixture_id"),
                "fixture_validation": validation,
                "evidence_status": provider_evidence.get("status"),
            })
            candidate["qualified"] = (
                candidate["source_market_locked"]
                and candidate["model_probability"] >= args.min_probability
                and candidate["ev"] >= args.min_ev
            )

        results.append({
            "fixture": resolved,
            "validation": validation,
            "evidence_status": provider_evidence.get("status"),
            "prediction_status": prediction.get("status"),
            "model": {
                "home_xg": prediction.get("home_xg"),
                "away_xg": prediction.get("away_xg"),
                "calibration": prediction.get("calibration"),
                "warnings": prediction.get("warnings"),
            },
            "markets": evaluated,
        })

    candidates = [
        m for r in results for m in r["markets"]
        if m.get("qualified")
    ]
    # Never select two markets from the same fixture.
    candidates.sort(key=lambda x: (x.get("ev", -999), x.get("model_probability", 0)), reverse=True)
    selected_5 = []
    selected_7 = []
    for c in candidates:
        if any(x["fixture_id"] == c["fixture_id"] for x in selected_7):
            continue
        selected_7.append(c)
        if len(selected_7) == 7:
            break
    selected_5 = selected_7[:5]

    output = {
        "engine_version": "V20.79",
        "baseline": "V20.78.52",
        "source": "PelangiEuro",
        "screenshots": screenshots,
        "parsed_by_screenshot": parsed_by_screenshot,
        "time_window": args.time_window,
        "time_filter_applied_after_provider_resolution": True,
        "time_filter_mode": "MANUAL",
        "market_source_locked": True,
        "no_forced_quota": True,
        "thresholds": {
            "minimum_probability": args.min_probability,
            "minimum_ev": args.min_ev,
        },
        "counts": {
            "input_screenshots": len(screenshots),
            "parsed_fixtures": len(fixtures),
            "resolved_fixtures": len(results),
            "unresolved_fixtures": len(unresolved),
            "qualified_markets": len(candidates),
        },
        "fixtures": results,
        "unresolved": unresolved,
        "candidates": candidates,
        "candidate_parlay_5": selected_5,
        "candidate_parlay_7": selected_7,
        "status": "PASS" if results else "NO_VALID_FIXTURES",
    }

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": output["status"],
        "counts": output["counts"],
        "candidate_parlay_5_legs": len(selected_5),
        "candidate_parlay_7_legs": len(selected_7),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
