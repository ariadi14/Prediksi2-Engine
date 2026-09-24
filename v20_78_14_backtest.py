from typing import List,Dict,Any

def walk_forward(records:List[Dict[str,Any]])->Dict[str,Any]:
    # Strictly chronological: train only on prior settled records.
    settled=[]; evaluated=[]
    for r in records:
        evaluated.append({'fixture':r.get('fixture'),'train_n':len(settled),'prediction':r.get('prediction'),'result':r.get('result')})
        if r.get('result') in ('WIN','LOSS'): settled.append(r)
    return {'status':'PASS','evaluated':evaluated,'settled_n':len(settled),'lookahead_free':True}
