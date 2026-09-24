# V20.78.17 — Full End-to-End Integration

Fixes the unfinished V20.78.16 path:
- one OCR pass per screenshot (no per-row OCR loops)
- dynamic N-fixture batch
- manual time filters; missing kickoff is never guessed
- provider enrichment runs in parallel with isolated failures
- provider results are cached in the batch map and then passed into the probability engine
- every visible screenshot market is retained
- final decision engine receives the calculated predictions
- no forced picks or parlay legs
- API keys are read only from environment variables

Supported environment variables:
- `API_FOOTBALL_KEY`
- `OPENFOOT_TOKEN`

API-Football documents fixture IDs as the master key for lineups, statistics, injuries, H2H, predictions and odds, and recommends checking competition coverage before downstream calls. The engine therefore treats missing coverage/data as missing evidence instead of fabricating values.
