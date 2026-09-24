"""V20.78.20 evidence quality gate."""
VERSION="V20.78.20"
WEIGHTS={"VERIFIED":1.0,"SINGLE_SOURCE":0.7,"CONFLICT":0.35,"MISSING":0.0}
def quality(ev):
 status=ev.get("evidence_status","MISSING") if isinstance(ev,dict) else "MISSING"
 fields=ev.get("fields",{}) if isinstance(ev,dict) else {}
 completeness=min(1.0,sum(v is not None for v in fields.values())/max(1,len(fields)))
 score=round(100*WEIGHTS.get(status,0)*(.5+.5*completeness),2)
 level="EXCELLENT" if score>=85 else "GOOD" if score>=65 else "FAIR" if score>=45 else "WEAK" if score>0 else "INSUFFICIENT"
 return {"score":score,"level":level,"status":status,"completeness":round(completeness,3)}
