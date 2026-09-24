"""V20.78.43 probability activation wrapper."""
from v20_78_37_probability_activation import ProbabilityActivation

def run(fixture_key,evidence,markets):
    return ProbabilityActivation().run(fixture_key,evidence,markets)
