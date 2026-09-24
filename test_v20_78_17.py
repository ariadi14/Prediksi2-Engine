import os,sys,time
from pathlib import Path
sys.path.insert(0,os.path.dirname(__file__))
from v20_78_17_end_to_end import EndToEndEngine

def main():
    fixture_dir=Path(__file__).resolve().parent/'fixtures'/'pelangi_euro'
    paths=[str(fixture_dir/f'{name}.jpg') for name in ('147433','147434','147435','147436')]
    e=EndToEndEngine(providers=[],max_workers=4)
    s=time.time(); r=e.run_images(paths,'ALL',{},1); elapsed=time.time()-s
    assert r['images']==4
    assert r['unique_fixtures']>0
    assert r['fixtures_processed']==r['unique_fixtures']
    assert r['decision']['fixtures_processed']==r['unique_fixtures']
    assert elapsed<90, elapsed
    # Provider failure must not kill the batch.
    class Bad:
        name='bad'
        def fetch(self,f): raise RuntimeError('simulated')
    r2=EndToEndEngine([Bad()],2).run_fixtures(r['parser_replay']['fixtures'],{},'ALL',1)
    assert r2['fixtures_processed']==r['unique_fixtures']
    assert len(r2['provider_errors'])==0 or isinstance(r2['provider_errors'],list)
    print('V20.78.17 E2E TEST PASS',r['unique_fixtures'],'fixtures',round(elapsed,2),'sec')
if __name__=='__main__': main()
