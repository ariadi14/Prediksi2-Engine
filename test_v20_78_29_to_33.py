import os,sys
from functools import lru_cache
from pathlib import Path
from v20_78_29_provider_identity import ProviderAwareTeamResolver
from v20_78_30_fixture_resolution import resolve_fixture_id
from v20_78_32_evidence_probability import EvidenceProbabilityGate
from v20_78_33_end_to_end import V33Engine

def test_provider_identity_local_fallback():
 r=ProviderAwareTeamResolver(catalog=[{'name':'Union La Calera','aliases':['Unión La Calera']},{'name':'Universidad Catolica','aliases':['CD Universidad Catolica']}])
 assert r.resolve('ye Union La Calera')['status']=='RESOLVED_HIGH'

def test_fixture_gate_blocks_without_provider():
 assert resolve_fixture_id({'home':'A','away':'B'},None)['status']=='UNRESOLVED'

def test_probability_gate_requires_evidence():
 p=EvidenceProbabilityGate().predict('x',{'evidence_status':'MISSING'},[])
 assert p['status']=='INSUFFICIENT_DATA'

@lru_cache(maxsize=1)
def _five_image_replay():
    from fast_pelangi_parser import FastPelangiParser
    fixture_dir=Path(__file__).resolve().parent/'fixtures'/'pelangi_euro'
    paths=tuple(str(fixture_dir/f'{name}.jpg') for name in ('147433','147434','147435','147436','147483'))
    return FastPelangiParser().replay(paths)

def test_replay_structure():
 r=_five_image_replay()
 assert r['time_filter_mode']=='MANUAL' and r['unique_fixtures']>=25

if __name__=='__main__':
 test_provider_identity_local_fallback();test_fixture_gate_blocks_without_provider();test_probability_gate_requires_evidence();test_replay_structure();print('V20.78.29-33 TEST PASS')

def test_regression_five_screenshots_exact_fixture_set():
    """Ground-truth regression: the five supplied screenshots contain 36 unique fixtures.
    Market rows may repeat for the same fixture and must be merged, not counted as fixtures.
    """
    fixture_dir=Path(__file__).resolve().parent/'fixtures'/'pelangi_euro'
    paths=[str(fixture_dir/f'{name}.jpg') for name in ('147433','147434','147435','147436','147483')]
    r=_five_image_replay()
    expected={
        ('Azerbaijan','Tajikistan'),('Gibraltar','Sao Tome and Principe'),
        ('Iraq','Oman'),('Saudi Arabia','Kuwait'),
        ('Italy U20 [w]','Spain U20 [w]'),('North Korea U20 [w]','Colombia U20 [w]'),
        ('Al Jazira Al Hamra','Forte Virtus FC'),('Hamilton Academical','Cowdenbeath'),
        ('SK Kladno','Banik Ostrava'),('Grorud IL','Moss'),
        ('UE Sant Andreu','Real Madrid Castilla'),('Boreham Wood','Everton U21'),
        ('Atletico Saguntino','CDA Navalcarnero'),('Guisborough Town','Ashington'),
        ('Lower Breck','Atherton Collieries'),('Shifnal Town','Nantwich Town'),
        ('Maccabi London FC','Biggleswade'),('Oud-Heverlee Leuven [w]','AS Roma [w]'),
        ('Servette Chenois [w]','Olympique Lyonnais [w]'),('PAOK [w]','Spartak Myjava [w]'),
        ('Slovan Liberec [w] [n]','Rosenborg [w]'),('HJK Helsinki [w]','Brann [w]'),
        ('Brondby IF [w]','Sporting Lisbon [w]'),('Tottenham Hotspur [w]','West Ham United [w]'),
        ('Crystal Palace [w]','Watford [w]'),('Nottingham Forest [w]','Aston Villa [w]'),
        ('Manchester United [w]','Sheffield United [w]'),('Liverpool [w]','Sunderland [w]'),
        ('Everton [w]','Birmingham City [w]'),('Seattle Sounders','Real Salt Lake'),
        ('America de Cali','Aguilas Doradas'),('Curico Unido','Deportes Concepcion'),
        ('Deportes Iquique','Antofagasta'),('Union La Calera','CD Universidad Catolica'),
        ('AD Tarma','Cienciano'),('Turks and Caicos Islands','Montserrat'),
    }
    actual={(f['home'],f['away']) for f in r['fixtures']}
    assert len(actual)==36
    assert actual==expected
    assert r['unique_fixtures']==36
