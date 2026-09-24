"""V20.78.51 true ensemble probability core.

Combines independent/explicit 1X2 probability sources with the score-matrix
baseline. Missing sources are omitted; weights are renormalized. No outcome
or probability is fabricated from absent evidence.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, Tuple
import math

EPS = 1e-12


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def norm3(h: float, d: float, a: float) -> Tuple[float, float, float]:
    vals = [max(EPS, float(h)), max(EPS, float(d)), max(EPS, float(a))]
    s = sum(vals)
    return tuple(v / s for v in vals)


def _prob(v: Any) -> Optional[float]:
    try:
        x = float(v)
        if 1 < x <= 100:
            x /= 100.0
        return x if 0 <= x <= 1 else None
    except (TypeError, ValueError):
        return None


def _explicit_1x2(e: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    raw = e.get("model_1x2")
    if not isinstance(raw, dict):
        return None
    h, d, a = (_prob(raw.get(k)) for k in ("Home", "Draw", "Away"))
    if None in (h, d, a):
        return None
    return norm3(h, d, a)


def _directional_component(e: Dict[str, Any], prefix: str, base: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    p = _prob(e.get(prefix))
    if p is None:
        return None
    # Directional sources predict home probability only. Keep draw mass from
    # the score model and split the remainder according to the source direction.
    _, draw, _ = base
    h = clamp(p)
    remainder = max(EPS, 1.0 - h)
    draw_mass = min(draw, remainder * 0.95)
    away = max(EPS, remainder - draw_mass)
    return norm3(h, draw_mass, away)


def _score_component(score_markets: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    raw = score_markets.get("1X2") if isinstance(score_markets, dict) else None
    if not isinstance(raw, dict):
        return None
    vals = tuple(_prob(raw.get(k)) for k in ("Home", "Draw", "Away"))
    return norm3(*vals) if None not in vals else None


DEFAULT_WEIGHTS = {
    "score_matrix": 0.34,
    "market_model": 0.18,
    "xg_context": 0.12,
    "form": 0.10,
    "home_away": 0.06,
    "elo": 0.08,
    "lineup": 0.07,
    "tactical": 0.03,
    "ml": 0.02,
}

KEYS = {
    "market_model": "model_1x2",
    "form": "form_home_prob",
    "home_away": "home_away_prob",
    "elo": "elo_home_prob",
    "lineup": "lineup_home_prob",
    "tactical": "tactical_home_prob",
    "ml": "ml_home_prob",
}


def _historical_reliability(e: Dict[str, Any], name: str) -> float:
    perf = e.get("model_performance", {}) or {}
    rec = perf.get(name, {}) if isinstance(perf, dict) else {}
    if not isinstance(rec, dict) or rec.get("brier") is None:
        return 1.0
    try:
        brier = float(rec["brier"])
        settled = max(0, int(rec.get("settled", 0) or 0))
    except (TypeError, ValueError):
        return 1.0
    if settled <= 0:
        return 1.0
    target = clamp(1.0 - brier / 0.30, 0.25, 1.25)
    shrink = min(1.0, settled / 50.0)
    return 1.0 + (target - 1.0) * shrink


def _quality_gate(e: Dict[str, Any]) -> float:
    status = str(e.get("evidence_status", "MISSING")).upper()
    return {"MISSING": 0.45, "SINGLE_SOURCE": 0.70, "CONFLICT": 0.60, "VERIFIED": 1.0}.get(status, 0.55)


def _weights(e: Dict[str, Any], available: Iterable[str]) -> Dict[str, float]:
    raw: Dict[str, float] = {}
    q = _quality_gate(e)
    for name in available:
        w = DEFAULT_WEIGHTS.get(name, 0.01) * _historical_reliability(e, name)
        if name in {"form", "home_away", "elo", "lineup", "tactical", "ml"}:
            w *= 0.70 + 0.30 * q
        raw[name] = max(EPS, w)
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


def build_true_ensemble(
    e: Dict[str, Any],
    score_markets: Dict[str, Any],
) -> Dict[str, Any]:
    """Return a calibrated-ready 1X2 ensemble and an audit trail."""
    base = _score_component(score_markets)
    if base is None:
        return {"status": "INSUFFICIENT_DATA", "probabilities": {}, "components": {}, "weights": {}}

    components: Dict[str, Tuple[float, float, float]] = {"score_matrix": base}
    explicit = _explicit_1x2(e)
    if explicit is not None:
        components["market_model"] = explicit

    # xG is represented by the score matrix; do not double-count it when no
    # independent xG probability distribution is supplied.
    xg_probs = e.get("xg_1x2")
    if isinstance(xg_probs, dict):
        vals = tuple(_prob(xg_probs.get(k)) for k in ("Home", "Draw", "Away"))
        if None not in vals:
            components["xg_context"] = norm3(*vals)

    for name, key in KEYS.items():
        if name in {"market_model"}:
            continue
        comp = _directional_component(e, key, base)
        if comp is not None:
            components[name] = comp

    weights = _weights(e, components.keys())
    out = [0.0, 0.0, 0.0]
    for name, comp in components.items():
        w = weights[name]
        for i in range(3):
            out[i] += w * comp[i]
    probs = norm3(*out)
    return {
        "status": "CALCULATED",
        "probabilities": {"Home": probs[0], "Draw": probs[1], "Away": probs[2]},
        "components": {k: {"Home": v[0], "Draw": v[1], "Away": v[2]} for k, v in components.items()},
        "weights": weights,
        "available_models": list(components.keys()),
    }
