from v20_78_3_live_providers import flatten_provider_payload, LiveEvidenceEnricher
class P:
    def __init__(self,n,p): self.name=n; self.p=p
    def fetch(self,f): return self.p
p={'predictions':{'response':[{'percent':{'home':'60','draw':'20','away':'20'},'comparison':{'att':{'home':'55','away':'45'},'def':{'home':'52','away':'48'}}}]}}
e=flatten_provider_payload(p)
assert abs(e['ml_home_prob']-.60)<1e-9
assert abs(e['home_attack']-.55)<1e-9
r=LiveEvidenceEnricher([P('a',p),P('b',p)]).enrich({'home':'A','away':'B'})
assert r['evidence_status']=='VERIFIED' and r['ml_home_prob']==.6
print('V20_78_3_LIVE_PROVIDER_TEST_PASS')
