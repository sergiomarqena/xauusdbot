from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.data.demo import DemoMarketDataProvider
from app.data.twelvedata import TwelveDataError, TwelveDataProvider
from app.domain.models import CandleSet, ProviderStatus
from app.services.research import build_research_overview
from app.services.terminal import build_terminal_snapshot

router = APIRouter(prefix="/api/v1")
VALID_INTERVALS = {"1min", "5min", "15min", "30min", "1h", "4h", "1day"}


def get_provider():
    settings = get_settings()
    provider_name = settings.data_provider.lower().strip()
    if provider_name == "demo":
        return DemoMarketDataProvider()
    if provider_name == "twelvedata":
        if not settings.twelve_data_api_key:
            return None
        return TwelveDataProvider(settings.twelve_data_api_key, settings.request_timeout_seconds)
    raise ValueError(f"Unsupported DATA_PROVIDER: {settings.data_provider}")


def _status(provider, settings) -> ProviderStatus:
    if provider is None:
        return ProviderStatus(
            provider="twelve-data",
            data_mode="unavailable",
            configured=False,
            symbol=settings.default_symbol,
            interval=settings.default_interval,
        )
    return ProviderStatus(
        provider=provider.name,
        data_mode=provider.data_mode,
        configured=provider.data_mode == "provider",
        symbol=settings.default_symbol,
        interval=settings.default_interval,
    )


@router.get("/market/status", response_model=ProviderStatus)
async def market_status():
    settings = get_settings()
    try:
        provider = get_provider()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _status(provider, settings)


async def _get_candle_set(symbol: str | None, interval: str | None, limit: int) -> CandleSet:
    settings = get_settings()
    selected_symbol = (symbol or settings.default_symbol).strip()
    selected_interval = (interval or settings.default_interval).strip()
    if selected_interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail=f"Unsupported interval. Choose one of: {sorted(VALID_INTERVALS)}")
    try:
        provider = get_provider()
        if provider is None:
            raise HTTPException(
                status_code=503,
                detail="Gold feed is not connected. Add TWELVE_DATA_API_KEY to Railway service variables.",
            )
        candles = await provider.get_candles(selected_symbol, selected_interval, limit)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TwelveDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CandleSet(
        symbol=selected_symbol,
        interval=selected_interval,
        provider=provider.name,
        data_mode=provider.data_mode,
        fetched_at=datetime.now(timezone.utc),
        candles=candles,
    )


@router.get("/market/candles")
async def market_candles(
    symbol: str | None = None,
    interval: str | None = None,
    limit: int = Query(default=200, ge=60, le=5000),
):
    return await _get_candle_set(symbol, interval, limit)


@router.get("/research/overview")
async def research_overview(
    symbol: str | None = None,
    interval: str | None = None,
    limit: int = Query(default=200, ge=60, le=5000),
):
    candle_set = await _get_candle_set(symbol, interval, limit)
    return build_research_overview(candle_set)


@router.get("/terminal/snapshot")
async def terminal_snapshot(
    interval: str = Query(default="1h"),
    limit: int = Query(default=200, ge=60, le=1000),
):
    settings = get_settings()
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=422, detail=f"Unsupported interval. Choose one of: {sorted(VALID_INTERVALS)}")

    provider = get_provider()
    gold = {
        "symbol": settings.default_symbol,
        "interval": interval,
        "provider": "twelve-data" if provider is None else provider.name,
        "data_mode": "unavailable" if provider is None else provider.data_mode,
        "status": "unavailable",
        "reason": "Connect a Twelve Data API key in Railway service variables to load live XAU/USD candles.",
        "candles": [],
        "measurements": None,
        "fetched_at": None,
    }
    if provider is not None:
        try:
            candles = await provider.get_candles(settings.default_symbol, interval, limit)
            candle_set = CandleSet(
                symbol=settings.default_symbol,
                interval=interval,
                provider=provider.name,
                data_mode=provider.data_mode,
                fetched_at=datetime.now(timezone.utc),
                candles=candles,
            )
            overview = build_research_overview(candle_set)
            gold.update({
                "status": "ok",
                "reason": None,
                "candles": [candle.model_dump(mode="json") for candle in candles],
                "measurements": overview["measurements"],
                "fetched_at": candle_set.fetched_at.isoformat(),
                "latest_candle": candles[-1].model_dump(mode="json") if candles else None,
            })
        except (TwelveDataError, ValueError) as exc:
            gold["reason"] = str(exc)[:240]

    context = await build_terminal_snapshot()
    return {
        "service": "NORDXAU.GPT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold": gold,
        **context,
    }
