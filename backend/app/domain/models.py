from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_ohlc_relationships(self):
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least as large as open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be no greater than open, close and high")
        return self


class CandleSet(BaseModel):
    symbol: str
    interval: str
    provider: str
    data_mode: Literal["demo", "provider", "unavailable"]
    fetched_at: datetime
    candles: list[Candle]


class ProviderStatus(BaseModel):
    provider: str
    data_mode: Literal["demo", "provider"]
    configured: bool
    symbol: str
    interval: str
