from v20_80_data_preparation import time_decay_weight, shrink_mean
from v20_80_model_audit import audit_model, adaptive_weights, ensemble_1x2


def test_time_decay_recent_is_higher():
    assert time_decay_weight("2026-09-20","2026-09-26") > time_decay_weight("2025-09-20","2026-09-26")


def test_shrinkage_moves_sparse_value_toward_prior():
    assert shrink_mean([2.0],1.0,5.0) == 7.0/6.0


def test_audit_metrics_need_settled_results():
    rows=[
        {"probabilities":{"Home":.6,"Draw":.2,"Away":.2},"result":"HOME"},
        {"probabilities":{"Home":.2,"Draw":.3,"Away":.5},"result":"AWAY"},
    ]
    m=audit_model(rows)
    assert m["settled"]==2
    assert m["brier"] is not None and m["log_loss"] is not None and m["rps"] is not None


def test_adaptive_weights_warmup_is_neutral():
    assert adaptive_weights({"a":{"settled":10,"brier":.1},"b":{"settled":10,"brier":.2}})=={"a":.5,"b":.5}


def test_ensemble_preserves_baseline_when_no_external_output():
    r=ensemble_1x2({"Home":.5,"Draw":.25,"Away":.25},{},{})
    assert r["status"]=="BASELINE_ONLY"
    assert r["probabilities"]["Home"]==.5
