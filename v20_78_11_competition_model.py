from typing import Dict,Any

def competition_profile(competition:str, history:Dict[str,Any]|None=None)->Dict[str,Any]:
    h=(history or {}).get(competition,{})
    n=int(h.get('n',0)); return {'competition':competition,'sample_size':n,'shrinkage':max(0.0,min(1.0,n/(n+50.0))) if n else 0.0,'status':'LEARNED' if n>=20 else 'WARMUP'}

def adjust_weight(base:float,competition:str,history:Dict[str,Any]|None=None)->float:
    p=competition_profile(competition,history); return base*(0.75+0.25*p['shrinkage'])
