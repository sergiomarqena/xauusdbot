from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.data.demo import DemoMarketDataProvider
from app.data.twelvedata import TwelveDataError, TwelveDataProvider
from app.domain.models import CandleSet, ProviderStatus
from app.services.research import build_research_overview

router = APIRouter(prefix="/api/v1")
VALID_INTERVALS = {"1min", "5min", "15min", "30min", "1h", "4h", "1day"}


def get_provider():
    settings = get_settings()
    provider_name = settings.data_provider.lower().strip()
    if provider_name == "demo":
        return DemoMarketDataProvider()
    if provider_name == "twelvedata":
        if not settings.twelve_data_api_key:
            raise ValueError("DATA_PROVIDER=twelvedata but TWELVE_DATA_API_KEY is not configured")
        return TwelveDataProvider(settings.twelve_data_api_key, settings.request_timeout_seconds)
    raise ValueError(f"Unsupported DATA_PROVIDER: {settings.data_provider}")


@router.get("/market/status", response_model=ProviderStatus)
async def market_status():
    settings = get_settings()
    try:
        provider = get_provider()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    configured = provider.data_mode == "provider"
    return ProviderStatus(
        provider=provider.name,
        data_mode=provider.data_mode,
        configured=configured,
        symbol=settings.default_symbol,
        interval=settings.default_interval,
    )


@router.get("/market/candles")
async def market_candles(
    symbol: str | None = None,
    interval: str | None = None,
    limit: int = Query(default=200, ge=60, le=5000),
):
    settings = get_settings()
    selected_symbol = (symbol or settings.default_symbol).strip()
    selected_interval = (interval or settings.default_interval).strip()
    if selected_interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail=f"Unsupported interval. Choose one of: {sorted(VALID_INTERVALS)}")
    try:
        provider = get_provider()
        candles = await provider.get_candles(selected_symbol, selected_interval, limit)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TwelveDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    candle_set = CandleSet(
        symbol=selected_symbol,
        interval=selected_interval,
        provider=provider.name,
        data_mode=provider.data_mode,
        fetched_at=datetime.now(timezone.utc),
        candles=candles,
    )
    return candle_set


@router.get("/research/overview")
async def research_overview(
    symbol: str | None = None,
    interval: str | None = None,
    limit: int = Query(default=200, ge=60, le=5000),
):
    candle_set = await market_candles(symbol=symbol, interval=interval, limit=limit)
    parsed = CandleSet.model_validate(candle_set)
    return build_research_overview(parsed)
