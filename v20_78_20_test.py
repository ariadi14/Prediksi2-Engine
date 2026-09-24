from v20_78_20_evidence_quality import quality
assert quality({"evidence_status":"VERIFIED","fields":{"xg":1,"form":2}})["level"]=="EXCELLENT"
assert quality({"evidence_status":"MISSING"})["level"]=="INSUFFICIENT"
print("V20.78.20 TEST PASS")
