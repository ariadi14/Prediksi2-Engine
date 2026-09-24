# V20.78.7 — Cross-Model Consistency & Uncertainty Engine

Adds cross-model agreement and uncertainty diagnostics to V20.78.6.

## New behavior
- Compares independently supplied model 1X2 distributions.
- Calculates model dispersion and agreement.
- Calculates normalized predictive entropy.
- Produces an uncertainty score/level using model agreement, entropy and evidence quality.
- Does not override probabilities solely because of uncertainty; it exposes the uncertainty for the decision gate.
- Preserves V20.78.6 dynamic weights and calibration warm-up.
