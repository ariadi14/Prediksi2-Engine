# V20.78.28 — Advanced Screenshot Parser + Team Identity Resolution

Adds a dedicated identity layer between PelangiEuro OCR and evidence providers.

Pipeline:
Screenshot -> OCR -> clean/normalize -> team identity -> fixture resolution -> evidence -> probability.

Rules:
- Team IDs are preferred when a provider supports them.
- Aliases and fuzzy matching are used only with confidence thresholds.
- Ambiguous identities are blocked; no silent guess.
- Historical CSV is an identity/evidence fallback and is explicitly labeled historical.
- Visible PelangiEuro markets remain the only selectable markets.
