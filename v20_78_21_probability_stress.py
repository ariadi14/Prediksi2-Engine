"""V20.78.21 probability stress/sensitivity checks."""
VERSION="V20.78.21"
def normalize(p):
 vals={k:max(0.0,float(v)) for k,v in p.items()}; t=sum(vals.values()); return {k:round(v/t*100,6) for k,v in vals.items()} if t else vals
def stress(probabilities, deltas=(.02,.05)):
 base=normalize(probabilities); tests=[]
 for d in deltas:
  shifted={k:(v/100)*(1+d) for k,v in base.items()}; tests.append({"delta":d,"probability":normalize(shifted)})
 return {"base":base,"tests":tests,"sum_ok":abs(sum(base.values())-100)<1e-6}
