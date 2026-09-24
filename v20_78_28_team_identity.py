"""V20.78.28 Team Identity Resolution.
PelangiEuro OCR names are resolved to canonical team identities before evidence lookup.
No low-confidence match is silently accepted.
"""
from __future__ import annotations
import re, unicodedata
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

OCR_NOISE = re.compile(r'^(?:je|/e|fe|ye|re|ie|te|ce|e)\s+', re.I)
ALIASES = {
    'ilton academical':'Hamilton Academical',
    'orth korea u20 [w]':'North Korea U20 [w]',
    'pain u20 [w]':'Spain U20 [w]',
    'america de cali':'America de Cali',
    'aguilas doradas':'Aguilas Doradas',
    'curico unido':'Curico Unido',
    'deportes concepcion':'Deportes Concepcion',
    'deportes iquique':'Deportes Iquique',
    'union la calera':'Union La Calera',
    'cd universidad catolica':'Universidad Catolica',
    'ad tarma':'AD Tarma',
    'turks and caicos islands':'Turks and Caicos Islands',
}

def clean_name(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('&',' and ')
    s = OCR_NOISE.sub('', s)
    s = re.sub(r'[^A-Za-z0-9\[\]().\- ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def norm_name(s: str) -> str:
    return re.sub(r'[^a-z0-9]','',clean_name(s).lower())


def _category_signature(s: str) -> str:
    x=clean_name(s).lower()
    sig=[]
    for tok in ('u21','u20','u19','u18','[w]','women','ladies','reserve','ii','b'):
        if tok in x: sig.append(tok)
    return '|'.join(sig)

class TeamIdentityResolver:
    def __init__(self, team_catalog: Optional[List[Dict[str,Any]]] = None):
        self.catalog = list(team_catalog or [])
        # Built-in canonical names let the resolver work even when the historical CSV
        # does not cover a competition. Live provider IDs can later supersede these.
        existing={norm_name(t.get('name')) for t in self.catalog if t.get('name')}
        for canonical in set(ALIASES.values()):
            if norm_name(canonical) not in existing:
                self.catalog.append({'name':canonical,'aliases':[]})
        self.alias_map = {norm_name(k):v for k,v in ALIASES.items()}
        self._index = {}
        for t in self.catalog:
            for key in [t.get('name'), *(t.get('aliases') or [])]:
                if key: self._index[norm_name(key)] = t

    def resolve(self, raw: str, candidates: Optional[List[Dict[str,Any]]] = None) -> Dict[str,Any]:
        cleaned = clean_name(raw)
        n = norm_name(cleaned)
        if not n:
            return {'status':'AMBIGUOUS','raw':raw,'cleaned':cleaned,'reason':'EMPTY_NAME'}
        alias = self.alias_map.get(n)
        if alias:
            n2=norm_name(alias)
            if n2 in self._index:
                t=self._index[n2]
                return self._result(raw,cleaned,t,100,'ALIAS_EXACT')
            cleaned=alias; n=n2
        if n in self._index:
            return self._result(raw,cleaned,self._index[n],100,'EXACT')
        pool = candidates if candidates is not None else self.catalog
        scored=[]
        for t in pool:
            names=[t.get('name',''), *(t.get('aliases') or [])]
            
            raw_sig=_category_signature(cleaned)
            valid_names=[x for x in names if x and (not raw_sig or _category_signature(x)==raw_sig)]
            if raw_sig and not valid_names:
                score=0
            else:
                score=max([fuzz.ratio(norm_name(x),n) for x in valid_names] or [0])
            if score>=60: scored.append((score,t))
        scored.sort(key=lambda x:x[0],reverse=True)
        if not scored: return {'status':'UNRESOLVED','raw':raw,'cleaned':cleaned,'reason':'NO_MATCH'}
        best=scored[0]; second=scored[1][0] if len(scored)>1 else 0
        if best[0] >= 92 and best[0]-second >= 5:
            return self._result(raw,cleaned,best[1],best[0],'FUZZY_HIGH')
        if best[0] >= 82 and best[0]-second >= 8:
            return self._result(raw,cleaned,best[1],best[0],'FUZZY_MEDIUM')
        return {'status':'AMBIGUOUS','raw':raw,'cleaned':cleaned,'best_score':best[0],'second_score':second,'reason':'CLOSE_MATCHES'}

    @staticmethod
    def _result(raw,cleaned,t,score,method):
        return {'status':'RESOLVED_HIGH' if score>=92 else 'RESOLVED_MEDIUM',
                'raw':raw,'cleaned':cleaned,'canonical_name':t.get('name'),
                'provider_ids':t.get('provider_ids',{}),'country':t.get('country'),
                'score':round(float(score),2),'method':method}

    def resolve_fixture(self, fixture: Dict[str,Any], home_candidates=None, away_candidates=None) -> Dict[str,Any]:
        h=self.resolve(fixture.get('home',''),home_candidates)
        a=self.resolve(fixture.get('away',''),away_candidates)
        out=dict(fixture)
        out['identity']={'home':h,'away':a}
        if h.get('status','').startswith('RESOLVED') and a.get('status','').startswith('RESOLVED'):
            out['home_canonical']=h.get('canonical_name'); out['away_canonical']=a.get('canonical_name')
            out['home_provider_ids']=h.get('provider_ids',{}); out['away_provider_ids']=a.get('provider_ids',{})
            out['identity_status']='RESOLVED'
        else:
            out['identity_status']='UNRESOLVED'
        return out
