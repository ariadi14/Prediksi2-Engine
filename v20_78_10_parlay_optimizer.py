from typing import List,Dict,Any
import math
from v20_78_9_correlation import correlation

def optimize(candidates:List[Dict[str,Any]], size:int=7, objective='balanced')->Dict[str,Any]:
    pool=[]
    for c in candidates:
        p=max(1e-6,min(0.999999,float(c.get('model_probability',0))))
        odds=float(c.get('odds',0) or 0)
        if p<=0 or odds<=1: continue
        value=p*odds-1
        score=(math.log(p)+0.15*max(-1,min(1,value))) if objective=='conservative' else (math.log(p)+0.30*max(-1,min(1,value)))
        pool.append((score,c))
    pool.sort(reverse=True,key=lambda z:z[0]); chosen=[]
    for _,c in pool:
        if any(correlation(c,x)>0.65 for x in chosen): continue
        chosen.append(c)
        if len(chosen)>=size: break
    joint=math.prod(max(1e-9,float(x.get('model_probability',0))) for x in chosen)
    total_odds=math.prod(float(x.get('odds',1)) for x in chosen)
    return {'status':'PASS' if chosen else 'NO_BET','legs':chosen,'size':len(chosen),'joint_probability':joint,'total_odds':total_odds}
