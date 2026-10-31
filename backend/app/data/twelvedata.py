from datetime import datetime, timezone

import httpx

from app.data.base import MarketDataProvider
from app.domain.models import Candle


class TwelveDataError(RuntimeError):
    """Raised when the upstream provider returns an error or unusable payload."""


class TwelveDataProvider(MarketDataProvider):
    name = "twelve-data"
    data_mode = "provider"
    endpoint = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key: str, timeout_seconds: float = 12.0):
        if not api_key.strip():
            raise ValueError("Twelve Data API key is required")
        self._api_key = api_key.strip()
        self._timeout = timeout_seconds

    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": limit,
            "order": "ASC",
            "timezone": "UTC",
            "apikey": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self.endpoint, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TwelveDataError(f"Twelve Data request failed: {exc}") from exc

        if payload.get("status") == "error" or "values" not in payload:
            message = payload.get("message", "Unexpected Twelve Data response")
            raise TwelveDataError(str(message))

        candles: list[Candle] = []
        for row in payload["values"]:
            try:
                stamp = datetime.fromisoformat(row["datetime"].replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                candles.append(
                    Candle(
                        timestamp=stamp,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]) if row.get("volume") not in (None, "") else None,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise TwelveDataError(f"Invalid candle received from Twelve Data: {exc}") from exc

        candles.sort(key=lambda candle: candle.timestamp)
        if not candles:
            raise TwelveDataError("Twelve Data returned an empty time series")
        return candles
