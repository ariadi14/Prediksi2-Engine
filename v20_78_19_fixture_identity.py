"""V20.78.26 fixture identity + fuzzy OCR resolution.
Resolves OCR-corrupted team/competition names without inventing a fixture.
"""
import re,unicodedata
from rapidfuzz import fuzz
VERSION='V20.78.26'

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+','',s)

def fixture_key(f): return '|'.join(norm(f.get(k,'')) for k in ('competition','home','away','match_date','kickoff'))

def _sim(a,b):
 a,b=norm(a),norm(b)
 if not a or not b:return 0.0
 if a==b:return 100.0
 return max(fuzz.ratio(a,b),fuzz.partial_ratio(a,b),fuzz.token_set_ratio(a,b))

def resolve_fixture(query,candidates,threshold=78,margin=5):
 qh,qa,qc=norm(query.get('home')),norm(query.get('away')),norm(query.get('competition'))
 scored=[]
 for c in candidates:
  hs=_sim(qh,c.get('home')); aas=_sim(qa,c.get('away')); cs=_sim(qc,c.get('competition')) if qc else 70
  # Team identity dominates; competition is a supporting signal.
  score=0.46*hs+0.46*aas+0.08*cs
  if qh and qa and hs<55 or qh and qa and aas<55: continue
  scored.append((score,hs,aas,cs,c))
 scored.sort(key=lambda x:x[0],reverse=True)
 if not scored:return None
 best=scored[0]
 second=scored[1][0] if len(scored)>1 else -1
 if best[0] < threshold or (second>=0 and best[0]-second < margin): return None
 out=dict(best[4]); out['_resolution']={'score':round(best[0],2),'home_similarity':round(best[1],2),'away_similarity':round(best[2],2),'competition_similarity':round(best[3],2)}
 return out
