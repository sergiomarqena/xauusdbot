from app.analytics.indicators import indicator_summary
from app.domain.models import CandleSet


def build_research_overview(candle_set: CandleSet) -> dict:
    """Return descriptive measurements only; do not turn them into a trade instruction."""
    summary = indicator_summary(candle_set.candles)
    latest = candle_set.candles[-1] if candle_set.candles else None
    return {
        "symbol": candle_set.symbol,
        "interval": candle_set.interval,
        "provider": candle_set.provider,
        "data_mode": candle_set.data_mode,
        "fetched_at": candle_set.fetched_at,
        "candle_count": len(candle_set.candles),
        "latest_candle": latest,
        "measurements": summary,
        "interpretation": "Descriptive market measurements only. No buy/sell call or probability claim is generated.",
    }
