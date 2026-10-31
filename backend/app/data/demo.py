import math
from datetime import datetime, timedelta, timezone

from app.data.base import MarketDataProvider
from app.domain.models import Candle


class DemoMarketDataProvider(MarketDataProvider):
    name = "deterministic-demo"
    data_mode = "demo"

    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        """Generate a repeatable illustrative series, never a representation of live prices."""
        minutes = _interval_minutes(interval)
        anchor = datetime(2025, 1, 1, tzinfo=timezone.utc)
        values: list[Candle] = []
        previous = 2650.0
        for i in range(limit):
            drift = 0.035 * i
            wave = 8.0 * math.sin(i / 8.0) + 2.8 * math.sin(i / 2.7)
            close = 2650.0 + drift + wave
            open_price = previous
            high = max(open_price, close) + 1.2 + abs(math.sin(i)) * 0.8
            low = min(open_price, close) - 1.1 - abs(math.cos(i)) * 0.7
            timestamp = anchor + timedelta(minutes=minutes * i)
            values.append(
                Candle(
                    timestamp=timestamp,
                    open=round(open_price, 3),
                    high=round(high, 3),
                    low=round(low, 3),
                    close=round(close, 3),
                    volume=None,
                )
            )
            previous = close
        return values


def _interval_minutes(interval: str) -> int:
    mapping = {"1min": 1, "5min": 5, "15min": 15, "30min": 30, "1h": 60, "4h": 240, "1day": 1440}
    if interval not in mapping:
        raise ValueError(f"Unsupported interval: {interval}")
    return mapping[interval]
