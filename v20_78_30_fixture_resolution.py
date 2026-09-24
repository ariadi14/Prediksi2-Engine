"""V20.78.30 fixture-ID resolution with strict identity/date/competition gates."""
from __future__ import annotations
from typing import Any,Dict
from rapidfuzz import fuzz
from v20_78_28_team_identity import clean_name,norm_name

def _score(a,b):
    return fuzz.ratio(norm_name(a),norm_name(b))

def resolve_fixture_id(fixture:Dict[str,Any], provider=None):
    out={'status':'UNRESOLVED','fixture_id':None,'candidates':[]}
    if not provider or not hasattr(provider,'find_fixture'): return out
    try: candidates=provider.find_fixture(fixture) or []
    except Exception as e:
        out['reason']=str(e)[:200]; return out
    scored=[]
    for c in candidates:
        th=c.get('home_name',''); ta=c.get('away_name','')
        hs=_score(fixture.get('home_canonical') or fixture.get('home',''),th)
        as_=_score(fixture.get('away_canonical') or fixture.get('away',''),ta)
        ds=1.0 if not fixture.get('match_date') or not c.get('date') or str(fixture.get('match_date'))==str(c.get('date')) else 0.0
        cs=1.0 if not fixture.get('competition') or not c.get('competition') else _score(fixture['competition'],c['competition'])/100
        total=0.45*hs+0.45*as_+10*ds+10*cs
        scored.append((total,c))
    scored.sort(key=lambda x:x[0],reverse=True)
    out['candidates']=[{'score':round(s,2),'fixture_id':c.get('fixture_id')} for s,c in scored[:5]]
    if not scored:return out
    best,second=scored[0],scored[1] if len(scored)>1 else (-999,{})
    if best[0]>=90 and best[0]-second[0]>=8:
        out.update({'status':'RESOLVED','fixture_id':best[1].get('fixture_id'),'match':best[1],'score':round(best[0],2)})
    else: out['reason']='AMBIGUOUS_OR_WEAK_MATCH'
    return out
