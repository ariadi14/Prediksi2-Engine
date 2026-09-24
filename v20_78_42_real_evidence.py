"""V20.78.42 evidence retrieval wrapper."""
from v20_78_36_evidence_retrieval import EvidenceService

def fetch(fixture, providers):
    return EvidenceService(providers).fetch(fixture)
