from typing import List,Dict,Any

def update_learning(records:List[Dict[str,Any]])->Dict[str,Any]:
    valid=[r for r in records if r.get('result') in ('WIN','LOSS')]
    wins=sum(r.get('result')=='WIN' for r in valid); n=len(valid)
    return {'valid_results':n,'wins':wins,'losses':n-wins,'win_rate':wins/n if n else None,'status':'CALIBRATED' if n>=20 else 'UNCALIBRATED'}
