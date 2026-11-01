from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "NORDXAU.GPT"
    data_provider: str = "twelvedata"
    twelve_data_api_key: str = ""
    coingecko_api_key: str = ""
    coinmarketcap_api_key: str = ""
    coinstats_api_key: str = ""
    default_symbol: str = "XAU/USD"
    default_interval: str = "1h"
    candle_limit: int = Field(default=200, ge=60, le=5000)
    request_timeout_seconds: float = Field(default=12.0, gt=0, le=60)

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
