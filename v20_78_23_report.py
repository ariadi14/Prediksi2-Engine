"""V20.78.23 final prediction report."""
VERSION="V20.78.23"
def build_report(result):
 pred=result.get("prediction",{})
 return {"version":VERSION,"fixture_key":result.get("fixture_key"),"probabilities":pred.get("probabilities",{}),"markets":result.get("market_candidates",[]),"evidence_quality":result.get("evidence_quality"),"uncertainty":pred.get("uncertainty"),"calibration":pred.get("calibration_status"),"report_status":"READY"}
