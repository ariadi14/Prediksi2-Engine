"""V20.78.29 provider-aware team identity resolution."""
from __future__ import annotations
import os,re,unicodedata
from typing import Any,Dict,List,Optional
from rapidfuzz import fuzz
from v20_78_28_team_identity import clean_name,norm_name,TeamIdentityResolver,_category_signature

class ProviderAwareTeamResolver:
    def __init__(self, provider=None, catalog=None):
        self.provider=provider
        self.local=TeamIdentityResolver(catalog or [])
    def _provider_candidates(self, raw:str):
        if not self.provider or not hasattr(self.provider,'search_teams'): return []
        try:return self.provider.search_teams(raw) or []
        except Exception:return []
    def resolve(self, raw:str, competition:str='', country:str=''):
        pc=self._provider_candidates(raw)
        if pc:
            r=self.local.resolve(raw,pc)
            if r.get('status','').startswith('RESOLVED'):
                r['method']='PROVIDER_'+r.get('method','MATCH')
                return r
        r=self.local.resolve(raw)
        if r.get('status','').startswith('RESOLVED'):
            r['method']='LOCAL_'+r.get('method','MATCH')
        return r
