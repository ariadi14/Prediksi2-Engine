from v20_78_18_live_validation import validate_provider_evidence
assert validate_provider_evidence({"evidence_status":"VERIFIED"})["status"]=="PASS"
print("V20.78.18 TEST PASS")
