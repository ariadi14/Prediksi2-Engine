from v20_78_45_historical_validation import validate
from v20_78_46_batch_validation import validate_batch
from v20_78_47_stress_test import run
from v20_78_48_calibration import calibrate
from v20_78_49_parlay_validation import validate as pv
from v20_78_50_production_gate import gate

def pred(train,test):
    return 0.7 if str(test.get('FTR'))=='H' else 0.3

def test_all():
    rows=[{'Date':f'2026-01-{i:02d}','Time':'12:00','FTR':'H' if i%2 else 'A'} for i in range(1,26)]
    h=validate(rows,pred,20); assert h['samples']==5
    b=validate_batch([{'validation':{'status':'VALID'},'evidence':{'status':'ENRICHED'},'prediction':{'status':'PASS'}}]); assert b['resolved']==1
    s=run([('bad',{})],lambda x:{'validation':{'status':'REJECTED'},'evidence':{'status':'MISSING'}}); assert s['passed']
    c=calibrate([(0.8,1),(0.2,0)],1.0); assert c['samples']==2
    p=pv([{'model_probability':.8,'odds':2.0,'fixture_id':'1'},{'model_probability':.75,'odds':2.1,'fixture_id':'2'}],sizes=(1,2)); assert '2' in p['runs']
    g=gate(True,False,True,True,True,True); assert not g['ready']
