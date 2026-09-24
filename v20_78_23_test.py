from v20_78_23_report import build_report
r=build_report({"fixture_key":"a","prediction":{"probabilities":{"home":50}},"market_candidates":[]}); assert r["report_status"]=="READY"
print("V20.78.23 TEST PASS")
