"""V20.78.40 provider connectivity gate."""
from v20_78_34_provider_connection import ProviderConnection

def status(api_key=None, openfoot_token=None):
    c=ProviderConnection(api_key,openfoot_token)
    return {'version':'V20.78.40','configured':c.configured,'status':c.status()}
