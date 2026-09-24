# V20.78.5 — Dedicated O/U & HDP Models

Adds dedicated market models for Over/Under and Asian Handicap. O/U is calculated directly from the score probability matrix and may blend explicit provider O/U probabilities. HDP is calculated line-by-line from the same matrix with quarter-line splitting and may blend explicit provider handicap probabilities. Only requested/visible lines should be passed by the pipeline. No missing values are fabricated.

## Tests
- V20_78_5_DEDICATED_OU_HDP_TEST_PASS
- Existing V20.78.4 ensemble test PASS
- Existing live provider test PASS
