from v20_78_19_fixture_identity import resolve_fixture,fixture_key
q={"competition":"Test Cup","home":"FC Alpha","away":"Beta United"}; cs=[{"competition":"Test Cup","home":"FC Alpha","away":"Beta United"}]
assert resolve_fixture(q,cs) is not None and fixture_key(q)
print("V20.78.19 TEST PASS")
