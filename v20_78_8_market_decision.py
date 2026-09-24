from typing import Any,Dict,List

def score_candidate(x:Dict[str,Any])->float:
    p=float(x.get('model_probability',0)); edge=float(x.get('edge') or 0); u=float(x.get('uncertainty',0.5))
    q=float(x.get('evidence_quality',0.5)); return 0.55*p+0.25*max(0,min(1,0.5+edge))*100/100+0.15*q+0.05*(1-u)

def select_markets(prediction:Dict[str,Any], visible:List[Dict[str,Any]], min_probability=0.50, min_edge=0.0)->List[Dict[str,Any]]:
    out=[]
    cal=prediction.get('calibration',{}); unc=cal.get('uncertainty',{}).get('score',0.5); q=cal.get('evidence_quality',0.5)
    for x in visible:
        p=x.get('model_probability')
        if p is None: continue
        y=dict(x); y.update({'uncertainty':unc,'evidence_quality':q})
        if float(p)>=min_probability and (y.get('edge') is None or float(y.get('edge') or 0)>=min_edge):
            y['decision_score']=score_candidate(y); y['decision']='PASS'
            out.append(y)
    return sorted(out,key=lambda z:z['decision_score'],reverse=True)
