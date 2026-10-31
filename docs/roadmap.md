# Roadmap

## Milestone 0 — Foundation (this scaffold)

- [x] Project structure and modular service boundary
- [x] FastAPI health and read-only research endpoints
- [x] Deterministic demo feed with visible demo label
- [x] Twelve Data OHLC adapter
- [x] EMA / RSI / ATR measurements
- [x] Multi-panel browser research console
- [x] Keyword-tagged bullish/bearish headline bubbles
- [x] BTC / XAU / WTI 1H, 4H, 1D and 1W trend-alignment matrix
- [x] Binance BTC taker-side flow and labelled XAU/WTI candle-volume proxies
- [x] Core tests

## Milestone 1 — Data integrity

- [ ] Verify Twelve Data symbol coverage, plan entitlements, and response behaviour for the intended XAU/USD feed
- [ ] Add provider health, retry/backoff, rate-limit handling, and stale-data detection
- [ ] Add SQLite/PostgreSQL repository and migrations
- [ ] Persist raw bars and data provenance
- [ ] Add scheduled ingestion with idempotent writes

## Milestone 2 — Research workspace

- [ ] Add DXY, yields, oil and economic-calendar adapters
- [ ] Add timestamp alignment and release-time handling
- [ ] Add event/news records with source URLs and timestamps
- [ ] Add transparent regime descriptors and feature versioning

## Milestone 3 — Historical evaluation

- [ ] Reproducible event-driven historical replay
- [ ] Realistic spread, fees, slippage and latency assumptions
- [ ] Walk-forward evaluation, holdout periods and baseline comparisons
- [ ] Paper-only portfolio ledger and audit trail

## Milestone 4 — Adaptive research

- [ ] Compare candidate models on rolling out-of-sample windows
- [ ] Monitor drift, calibration and stability
- [ ] Retire candidates that fail pre-registered validation criteria
- [ ] Show uncertainty and abstain when evidence is weak

A milestone is complete only when tests, data provenance, and limitations are documented. A visually attractive dashboard is not evidence of predictive skill.
