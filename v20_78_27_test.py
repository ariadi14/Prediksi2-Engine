from pathlib import Path
from functools import lru_cache
from fast_pelangi_parser import FastPelangiParser
from v20_78_19_fixture_identity import resolve_fixture
from v20_78_17_end_to_end import EndToEndEngine

FIXTURE_DIR=Path(__file__).resolve().parent/'fixtures'/'pelangi_euro'
IMAGES=[str(FIXTURE_DIR/f'{name}.jpg') for name in ('147433','147434','147435','147436')]

@lru_cache(maxsize=1)
def _replay():
    return FastPelangiParser().replay(tuple(IMAGES))

def test_parser_names():
    r=_replay()
    names={(f['home'],f['away']) for f in r['fixtures']}
    assert ('Hamilton Academical','Cowdenbeath') in names
    assert ('SK Kladno','Banik Ostrava') in names
    assert ('Boreham Wood','Everton U21') in names

def test_fuzzy_resolution():
    q={'competition':'SCOTLAND CHALLENGE CUP','home':'ilton Academical','away':'Cowdenbeath'}
    c=[{'competition':'SCOTLAND CHALLENGE CUP','home':'Hamilton Academical','away':'Cowdenbeath'}]
    r=resolve_fixture(q,c)
    assert r is not None and r['_resolution']['score']>=78

def test_e2e_synthetic_evidence():
    r=_replay()
    f=next(x for x in r['fixtures'] if x['home']=='Azerbaijan' and x['away']=='Tajikistan')
    key=EndToEndEngine().key(f)
    ev={key:{'home_xg':1.55,'away_xg':0.72,'evidence_quality':0.8}}
    out=EndToEndEngine().run_fixtures([f],ev)
    assert out['results'][0]['prediction']['status']=='CALCULATED'
    assert out['results'][0]['visible_candidates']

def test_e2e_parser_count():
    replay=_replay()
    r=EndToEndEngine().run_fixtures(replay['fixtures'],{},'ALL',1)
    assert len(replay['fixtures'])>=25
    assert r['fixtures_processed']==len(replay['fixtures'])

if __name__=='__main__':
    test_parser_names(); test_fuzzy_resolution(); test_e2e_synthetic_evidence(); test_e2e_parser_count(); print('V20.78.27 TEST PASS')
