"""V20.78.48 probability calibration utilities."""
import math

def brier(pairs):
    vals=[(float(p)-float(y))**2 for p,y in pairs]
    return sum(vals)/len(vals) if vals else None

def temperature_scale(logits, temperature=1.0):
    t=max(0.05,float(temperature))
    return [1/(1+math.exp(-float(x)/t)) for x in logits]

def calibrate(pairs, temperature=1.0):
    # pairs are (probability, actual); temperature is applied in logit space.
    logits=[]
    ys=[]
    for p,y in pairs:
        p=min(.999999,max(.000001,float(p)))
        logits.append(math.log(p/(1-p))); ys.append(int(y))
    calibrated=temperature_scale(logits,temperature)
    return {"version":"V20.78.48","temperature":temperature,
            "raw_brier":brier(pairs),"calibrated_brier":brier(list(zip(calibrated,ys))),
            "samples":len(pairs)}
