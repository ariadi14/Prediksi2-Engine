"""V20.78.47 adversarial/stress validation."""
def run(cases, runner):
    out=[]
    for name,fixture in cases:
        try:
            r=runner(fixture)
            safe = r.get("validation",{}).get("status") != "VALID" or r.get("evidence",{}).get("status") == "ENRICHED"
            out.append({"case":name,"passed":bool(safe),"result":r})
        except Exception as e:
            out.append({"case":name,"passed":False,"error":str(e)})
    return {"version":"V20.78.47","passed":all(x["passed"] for x in out),"cases":out}
