"""V20.78.45 leakage-safe historical validation."""
from v20_78_22_walkforward import walk_forward, brier_binary

def validate(rows, predictor, min_train=20):
    wf = walk_forward(rows, predictor, min_train=min_train)
    return {"version":"V20.78.45","samples":len(wf),"brier":brier_binary(wf),"results":wf}
