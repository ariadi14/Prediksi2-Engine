"""V20.78.49 parlay validation without forcing weak legs."""
from v20_78_10_parlay_optimizer import optimize

def validate(candidates, sizes=(3,5,7)):
    runs={}
    for n in sizes:
        r=optimize(candidates,size=n,objective='balanced')
        runs[str(n)]={k:r[k] for k in ('status','size','joint_probability','total_odds')}
    return {"version":"V20.78.49","runs":runs}
