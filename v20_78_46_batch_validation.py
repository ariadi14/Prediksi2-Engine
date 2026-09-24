"""V20.78.46 batch screenshot/prediction validation."""
def validate_batch(results):
    return {
      "version":"V20.78.46",
      "fixtures":len(results),
      "resolved":sum(r.get("validation",{}).get("status")=="VALID" for r in results),
      "evidence_enriched":sum(r.get("evidence",{}).get("status")=="ENRICHED" for r in results),
      "predictions":sum(r.get("prediction",{}).get("status") not in (None,"INSUFFICIENT_DATA") for r in results),
      "no_bet":sum(r.get("prediction",{}).get("status")=="INSUFFICIENT_DATA" for r in results)
    }
