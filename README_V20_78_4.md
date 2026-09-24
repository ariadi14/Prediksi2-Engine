# V20.78.4 — Evidence-Weighted Market Ensemble

Adds an explicit ensemble layer after the V20.78 score-probability matrix.

- Blends score-matrix 1X2 with explicit provider 1X2 probabilities when available.
- If only directional context exists, blends it transparently and preserves probability sum = 100%.
- Records component weights and provenance status.
- Adds evidence-aware market confidence (descriptive, not a guarantee).
- Never fabricates missing evidence.
- Works with any number of fixtures.

This release does not claim live data availability until provider credentials/endpoints are configured.
