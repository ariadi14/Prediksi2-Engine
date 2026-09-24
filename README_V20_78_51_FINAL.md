# Prediksi 2 — V20.78.51 FINAL CANDIDATE

Implements the V20.78.51 upgrade plan through the final validation gate.

## Guarantees
- Parser/fixture resolver regression is preserved.
- Manual time-filter architecture is preserved.
- Source-market lock: only market + exact line + selection visible in the submitted source may become a candidate.
- No forced parlay quota.
- 1X2 uses the V20.78.51 true ensemble when required inputs exist.
- Score matrix remains the common probability distribution for 1X2/O-U/HDP.
- Market value exposes implied probability, de-vig market probability, fair odds, edge and EV.
- Calibration is market-specific and remains uncalibrated until enough settled samples exist.
- Data confidence and qualification are explicit.
- Production gate remains NOT_READY until real provider/evidence and out-of-sample validation pass.

## Status
This ZIP is a final engineering candidate, not a claim of profitable betting performance.


## V20.78.52 Data Acquisition Extension
- Free-first provider orchestration with automatic fallback.
- QuotaManager prevents requests after provider quota exhaustion.
- TTLCache reuses fresh fixture/H2H/form/injury/lineup/statistics/xG/standings data.
- Missing data remains `MISSING`; it is never converted to zero or fabricated.
- FootballDataCSV supports an optional local historical CSV when the file is actually present.
- This extension does not make production readiness claims; real provider/evidence validation is still required.
