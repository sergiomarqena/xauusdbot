# Architecture — v0.1

## Design target

Keep the first release small, observable and replaceable. Providers, analytics and API routes are separate modules so a data-source change does not rewrite the research logic.

## Logical flow

```text
Market data provider
        │
        ▼
Provider adapter ──► validated Candle domain model
                            │
                            ▼
                    analytics functions
                            │
                            ▼
                    research overview API
                            │
                            ▼
                     browser dashboard
```

## Layers

- **Provider adapters:** deterministic demo provider now; Twelve Data OHLC adapter when explicitly configured. Future adapters must satisfy the same interface.
- **Domain:** validated, immutable candle objects. Timestamps are timezone-aware; prices must be positive and OHLC relationships must be valid.
- **Analytics:** pure functions for EMA, RSI and ATR. They do not access the network or make execution decisions.
- **Research service:** packages source metadata and measurements. It must never disguise demo data as externally sourced data.
- **API:** read-only HTTP routes. No account, broker, order, or position endpoints.
- **Frontend:** read-only dashboard; it displays provider mode and execution-disabled status.

## Planned evolution

1. Add durable storage for raw candles and provider metadata.
2. Add macro/event/news ingestion as separate timestamped evidence streams.
3. Add feature and hypothesis versioning.
4. Add a reproducible historical replay and backtest package.
5. Add paper-only portfolio simulation with explicit spread, fees, slippage, and audit logs.
6. Add a walk-forward evaluation and drift-monitoring layer.
7. Only after data quality and validation are established, consider a richer research interface.

No AI-generated narrative should overwrite raw data or numerical results. AI outputs, once introduced, must cite the exact data window and evidence objects used.
