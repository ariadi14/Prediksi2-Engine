"""V20.78.34 provider connection/configuration and explicit health states."""
import os
from typing import Any, Dict, Optional
from v20_78_3_live_providers import APIFootballProvider
from v20_78_52_data_acquisition import FootballDataFixtureCSV, LocalFootballDatabase

class ProviderConnection:
    def __init__(self, api_key: Optional[str]=None, openfoot_token: Optional[str]=None):
        # V20.79 production policy: API-Football is the only live provider.
        # When its daily quota is exhausted, fall back to the local CSV layer.
        # OpenFoot is intentionally not instantiated or used.
        self.api_key = api_key or os.getenv('API_FOOTBALL_KEY')
        self.csv_path = os.getenv('FOOTBALL_DATA_CSV_PATH', 'data/football_data.csv')
        self.database_path = os.getenv('FOOTBALL_DATABASE_PATH', 'data/database/football.db')
        self.providers=[]
        if self.api_key:
            self.providers.append(APIFootballProvider(self.api_key))
        self.providers.append(FootballDataFixtureCSV(self.csv_path))
        self.providers.append(LocalFootballDatabase(self.database_path))
    @property
    def configured(self):
        # `configured` represents live-provider credential readiness.
        # Historical CSV/SQLite providers remain available as fallbacks but
        # must not make an otherwise unconfigured live connection appear ready.
        return bool(self.api_key)
    def status(self):
        return {'configured':self.configured,'providers':[getattr(p,'name',p.__class__.__name__) for p in self.providers],
                'live_provider':'api-football' if self.api_key else None,
                'historical_fallback':'football-data-csv' if os.path.isfile(self.csv_path) else ('football-local-db' if os.path.isfile(self.database_path) else None),
                'reason':None if self.configured else 'NO_PROVIDER_CREDENTIAL_CONFIGURED'}
