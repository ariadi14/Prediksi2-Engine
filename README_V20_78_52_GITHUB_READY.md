# Prediksi 2 — V20.78.52 GitHub Ready

This package is the pre-GitHub integration candidate for the V20.78.52 Data Acquisition layer.

## Entity-aware rules
- CLUB and NATIONAL teams are classified separately.
- WOMEN, U21, U23 and YOUTH are isolated from senior men's entities.
- Generic competition names are not silently mapped to a country-specific competition.
- National-team data is never treated as club-league data.

## Provider routing
1. API-Football: broad primary provider.
2. Sportmonks: restricted to Danish Superliga and Scottish Premiership.
3. football-data.org: fallback where coverage is available.
4. Cache: used before another provider request when fresh data exists.
5. Missing data remains MISSING; it is never converted to zero or negative evidence.

## Market integrity
The screenshot remains the sole authority for market, line and selection. Provider data only supports fixture/evidence analysis and never invents a market or changes a line.

## Validation
The integrated local regression suite currently passes **58 tests**.

Production readiness is not asserted here: real-provider verification and the existing production gate must still pass in GitHub Actions.
