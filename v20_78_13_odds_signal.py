from typing import List,Dict,Any

def odds_signal(history:List[float])->Dict[str,Any]:
    vals=[float(x) for x in history if float(x)>1]
    if len(vals)<2:return {'status':'INSUFFICIENT_DATA','direction':None,'movement':None}
    movement=vals[-1]-vals[0]
    return {'status':'CALCULATED','direction':'SHORTENING' if movement<0 else 'DRIFTING' if movement>0 else 'FLAT','movement':movement,'from':vals[0],'to':vals[-1]}
