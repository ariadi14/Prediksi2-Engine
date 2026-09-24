# V20.78.50 Parser Regression Fix

## Scope

This patch hardens the PelangiEuro screenshot parser and its regression tests without changing the V20.78.50 production gate.

## Ground-truth fixtures

The five supplied screenshots are kept byte-for-byte unchanged:

- `fixtures/pelangi_euro/147433.jpg`
- `fixtures/pelangi_euro/147434.jpg`
- `fixtures/pelangi_euro/147435.jpg`
- `fixtures/pelangi_euro/147436.jpg`
- `fixtures/pelangi_euro/147483.jpg`

## Parser fixes

- OCR crop starts high enough to capture fixtures beginning near the top of a screenshot.
- Top competition-bar recovery handles headers that sit just above the normal fixture crop.
- Team-name normalization removes common OCR prefixes/noise and normalizes accents.
- Known OCR variants such as `Universidad Catolica`/`CD Universidad Catolica` are canonicalized.
- Repeated market rows for the same fixture are merged instead of counted as separate fixtures.
- Market entries remain attached to the merged fixture and source image IDs are retained.

## Regression expectation

The five screenshots contain **36 unique visible fixtures**. Repeated 1X2/HDP market rows must not increase the fixture count.

The regression test verifies the exact 36 home/away pairs, not merely `unique_fixtures >= 25`.

## Validation

```text
pytest -q
24 passed

pytest -q test_v20_78_45_to_50.py
1 passed

Production gate:
version = V20.78.50
status  = NOT_READY
ready   = False
```

`NOT_READY` remains intentional because the production gate still requires real provider data/evidence validation. This patch does not weaken that gate.
