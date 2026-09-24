from v20_78_28_team_identity import TeamIdentityResolver

def test_alias_and_fuzzy():
    cat=[{'name':'Union La Calera','aliases':['Unión La Calera']},{'name':'Universidad Catolica','aliases':['CD Universidad Catolica']}]
    r=TeamIdentityResolver(cat)
    assert r.resolve('ye Union La Calera')['status']=='RESOLVED_HIGH'
    assert r.resolve('CD Universidad Catolica')['canonical_name']=='Universidad Catolica'

def test_ambiguous_is_blocked():
    r=TeamIdentityResolver([{'name':'United FC'},{'name':'United SC'}])
    assert r.resolve('United')['status']=='AMBIGUOUS'

if __name__=='__main__':
    test_alias_and_fuzzy(); test_ambiguous_is_blocked(); print('V20.78.28 TEST PASS')
