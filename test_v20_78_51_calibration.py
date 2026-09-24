from v20_78_51_calibration import brier,log_loss,ece,binary_temperature_fit

def test_metrics():
    pairs=[(.9,1),(.1,0),(.8,1),(.2,0)]
    assert brier(pairs) < .05 and log_loss(pairs) > 0 and ece(pairs) >= 0

def test_warmup_gate():
    assert binary_temperature_fit([(.5,1),(.5,0)])['status']=='UNCALIBRATED'
