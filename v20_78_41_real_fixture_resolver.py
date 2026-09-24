"""V20.78.41 provider-aware fixture resolver wrapper."""
from v20_78_39_provider_aware_pipeline import ProviderAwarePipeline

def resolve(fixture, connection=None):
    return ProviderAwarePipeline(connection).resolve_fixture(fixture)
