from v20_78_51_probability_core import build_true_ensemble


def test_true_ensemble_uses_multiple_components_and_normalizes():
    e = {
        "evidence_status": "VERIFIED",
        "model_1x2": {"Home": 0.55, "Draw": 0.25, "Away": 0.20},
        "form_home_prob": 0.62,
        "elo_home_prob": 0.58,
    }
    score = {"1X2": {"Home": 0.50, "Draw": 0.28, "Away": 0.22}}
    out = build_true_ensemble(e, score)
    p = out["probabilities"]
    assert out["status"] == "CALCULATED"
    assert set(("score_matrix", "market_model", "form", "elo")).issubset(out["available_models"])
    assert abs(sum(p.values()) - 1.0) < 1e-12
    assert abs(sum(out["weights"].values()) - 1.0) < 1e-12


def test_missing_context_does_not_get_fabricated():
    e = {"evidence_status": "MISSING"}
    score = {"1X2": {"Home": 0.40, "Draw": 0.30, "Away": 0.30}}
    out = build_true_ensemble(e, score)
    assert out["available_models"] == ["score_matrix"]
    assert out["probabilities"] == {"Home": 0.4, "Draw": 0.3, "Away": 0.3}


def test_historical_brier_changes_weight_without_breaking_normalization():
    e = {
        "evidence_status": "VERIFIED",
        "model_1x2": {"Home": 0.55, "Draw": 0.25, "Away": 0.20},
        "form_home_prob": 0.60,
        "model_performance": {"form": {"brier": 0.10, "settled": 100}},
    }
    score = {"1X2": {"Home": 0.50, "Draw": 0.28, "Away": 0.22}}
    out = build_true_ensemble(e, score)
    assert out["weights"]["form"] > 0
    assert abs(sum(out["probabilities"].values()) - 1.0) < 1e-12
