from abc import ABC, abstractmethod

from app.domain.models import Candle


class MarketDataProvider(ABC):
    name: str
    data_mode: str

    @abstractmethod
    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        """Return candles sorted oldest to newest."""
