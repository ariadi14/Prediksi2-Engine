from v20_78_52_data_acquisition import TTLCache,QuotaManager,DataAcquisitionManager,FootballDataCSV

class P:
    def __init__(self,name,data): self.name=name; self.data=data; self.calls=0
    def fetch(self,fixture): self.calls+=1; return self.data

def test_quota_blocks_after_limit():
    q=QuotaManager({'a':1}); assert q.can_request('a'); assert q.consume('a'); assert not q.can_request('a')

def test_fallback_to_second_provider():
    a=P('a',{}); b=P('b',{'h2h':{'ok':1}})
    m=DataAcquisitionManager([a,b],QuotaManager({'a':1,'b':2}),TTLCache())
    r=m.acquire({'fixture_id':1},['h2h']); assert r['h2h']=={'ok':1}; assert r['acquisition_meta']['h2h']['source']=='b'

def test_cache_avoids_new_request():
    a=P('a',{'h2h':{'ok':1}}); q=QuotaManager({'a':1}); c=TTLCache(); m=DataAcquisitionManager([a],q,c)
    f={'fixture_id':2}; m.acquire(f,['h2h']); r=m.acquire(f,['h2h']); assert a.calls==1; assert r['acquisition_meta']['h2h']['status']=='CACHED'

def test_missing_is_not_zero():
    a=P('a',{}); r=DataAcquisitionManager([a],QuotaManager({'a':1}),TTLCache()).acquire({'fixture_id':3},['xg'])
    assert r['xg'] is None and r['acquisition_meta']['xg']['status']=='MISSING'

def test_csv_missing_is_safe(tmp_path):
    c=FootballDataCSV(str(tmp_path/'missing.csv')); assert not c.available(); assert c.rows()==[]
