"""V20.78.35 strict fixture validation independent of kickoff availability."""
from rapidfuzz import fuzz
from v20_78_28_team_identity import norm_name

def validate_fixture(f, candidate, min_team=90, min_comp=55):
    if not candidate or candidate.get('fixture_id') is None: return {'status':'REJECTED','reason':'NO_FIXTURE_ID'}
    h=fuzz.ratio(norm_name(f.get('home_canonical') or f.get('home','')), norm_name(candidate.get('home_name','')))
    a=fuzz.ratio(norm_name(f.get('away_canonical') or f.get('away','')), norm_name(candidate.get('away_name','')))
    c=fuzz.ratio(norm_name(f.get('competition','')), norm_name(candidate.get('competition',''))) if f.get('competition') and candidate.get('competition') else 100
    d=1 if not f.get('match_date') or not candidate.get('date') or str(f['match_date'])==str(candidate['date']) else 0
    ok=h>=min_team and a>=min_team and c>=min_comp and d==1
    return {'status':'VALID' if ok else 'REJECTED','home_score':round(h,1),'away_score':round(a,1),'competition_score':round(c,1),'date_ok':bool(d),'fixture_id':candidate.get('fixture_id')}
