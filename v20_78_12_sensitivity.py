from typing import Dict,Any

def sensitivity(base:Dict[str,float], scenarios:Dict[str,Dict[str,float]])->Dict[str,Any]:
    out={'BASE':dict(base)};
    for name,sc in scenarios.items(): out[name]={k:float(sc.get(k,base[k])) for k in base}
    ranges={k:max(v[k] for v in out.values())-min(v[k] for v in out.values()) for k in base} if out else {k:0 for k in base}
    return {'scenarios':out,'sensitivity_range':ranges,'max_change':max(ranges.values()) if ranges else 0.0}
