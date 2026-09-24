"""V20.78.34 provider connection/configuration and explicit health states."""
import os
from typing import Any, Dict, Optional
from v20_78_3_live_providers import APIFootballProvider, OpenFootProvider

class ProviderConnection:
    def __init__(self, api_key: Optional[str]=None, openfoot_token: Optional[str]=None):
        self.api_key = api_key or os.getenv('API_FOOTBALL_KEY')
        self.openfoot_token = openfoot_token or os.getenv('OPENFOOT_TOKEN')
        self.providers=[]
        if self.api_key: self.providers.append(APIFootballProvider(self.api_key))
        if self.openfoot_token: self.providers.append(OpenFootProvider(self.openfoot_token))
    @property
    def configured(self): return bool(self.providers)
    def status(self):
        return {'configured':self.configured,'providers':[getattr(p,'name',p.__class__.__name__) for p in self.providers],
                'reason':None if self.configured else 'NO_PROVIDER_CREDENTIAL_CONFIGURED'}
