# Data contracts — v0.1

## Candle

Each candle contains `timestamp`, `open`, `high`, `low`, `close`, and optional `volume`.

Validation requirements:

- Timestamp must include a timezone.
- All prices must be positive.
- `high` cannot be lower than `low`, `open`, or `close`.
- `low` cannot be higher than `open` or `close`.
- A returned series is sorted oldest to newest.
- Provider, symbol, interval, fetch time, and data mode travel with the series.

## Provenance

Every persisted observation should eventually carry:

- provider and provider instrument identifier;
- requested and normalized symbol;
- timeframe / interval;
- source timestamp and ingestion timestamp;
- timezone and session convention;
- whether the observation is demo or externally sourced; also preserve the provider-reported delay/entitlement metadata when available;
- raw response hash or source reference where permitted.

## Missing or stale data

Do not forward-fill market prices silently. Missing bars and provider errors must be visible. A failed live provider request must return an error; it must not silently fall back to demo data.

## Related instruments

The long-term research scope may include DXY, U.S. yields, oil, rates expectations, and event calendars. These are independent data streams with distinct calendars and update frequencies; they should not be merged into one synthetic candle series.
