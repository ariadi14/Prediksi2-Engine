"""V20.78.18 live-provider validation utilities."""
VERSION="V20.78.18"
def validate_provider_evidence(ev):
    if not isinstance(ev,dict): return {"status":"INVALID","issues":["not_dict"]}
    status=ev.get("evidence_status","MISSING")
    ok=status in {"VERIFIED","SINGLE_SOURCE","CONFLICT","MISSING"}
    return {"status":"PASS" if ok else "FAIL","evidence_status":status,"issues":[] if ok else ["invalid_status"]}
