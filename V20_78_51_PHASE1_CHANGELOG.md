# V20.78.51 — Phase 1 Probability Core

Baseline: `V20.78.50 FINAL VALIDATION CANDIDATE PARSER REGRESSION FIX WITH WORKFLOW`

## Implemented
- True 1X2 ensemble layer in `v20_78_51_probability_core.py`.
- Score-matrix probability remains the structural baseline.
- Explicit provider/model 1X2 probability can be combined when present.
- Independent context signals supported: form, home/away, Elo, lineup, tactical, ML, and optional xG 1X2.
- Missing signals are omitted; no probability is fabricated.
- Ensemble weights are renormalized over available components.
- Historical Brier performance can adjust component reliability with shrinkage.
- Evidence quality gates contextual models.
- Full component and weight audit trail is returned.
- Existing probability engine now consumes the V20.78.51 ensemble for 1X2.

## Compatibility
- Parser and fixture resolver were not modified.
- Existing O/U and HDP score-matrix paths remain intact.
- Existing calibration and production gate remain intact.
- `V20.78.50` regression tests remain mandatory.

## Validation
- New V20.78.51 probability tests: **3 passed**
- Existing V20.78.45–50 regression tests: **4 passed**
- Full local suite: **27 passed**

This is **not** a production-readiness declaration. Real provider/evidence validation, calibration proof, market value/de-vig, market lock, and out-of-sample validation remain required by the V20.78.51 plan.
