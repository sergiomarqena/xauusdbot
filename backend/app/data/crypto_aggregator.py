from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

CACHE: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 60


def _cached(key: str):
    item = CACHE.get(key)
    if item and item[0] > asyncio.get_event_loop().time():
        return item[1]
    return None


def _save(key: str, value: Any):
    CACHE[key] = (asyncio.get_event_loop().time() + CACHE_TTL, value)
    return value


def _normalise(row: dict, source: str, price: Any, change: Any, volume: Any, market_cap: Any, updated: Any = None) -> dict:
    def number(value):
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
    return {
        "id": str(row.get("id") or row.get("slug") or row.get("symbol") or "").lower(),
        "name": row.get("name"),
        "symbol": str(row.get("symbol") or "").upper(),
        "price_usd": number(price),
        "change_24h_pct": number(change),
        "volume_24h_usd": number(volume),
        "market_cap_usd": number(market_cap),
        "source": source,
        "updated_at": updated or datetime.now(timezone.utc).isoformat(),
    }


async def _coingecko(client: httpx.AsyncClient, key: str) -> dict:
    if not key:
        return {"status": "not_configured", "source": "CoinGecko", "coins": []}
    cache_key = "coingecko"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1, "sparkline": "false"},
            headers={"x-cg-demo-api-key": key},
        )
        response.raise_for_status()
        rows = response.json()
        coins = [_normalise(
            row, "CoinGecko", row.get("current_price"), row.get("price_change_percentage_24h"),
            row.get("total_volume"), row.get("market_cap"), row.get("last_updated"),
        ) for row in rows if isinstance(row, dict)]
        return _save(cache_key, {"status": "ok", "source": "CoinGecko", "coins": coins})
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"status": "error", "source": "CoinGecko", "coins": [], "error": str(exc)[:180]}


async def _coinmarketcap(client: httpx.AsyncClient, key: str) -> dict:
    if not key:
        return {"status": "not_configured", "source": "CoinMarketCap", "coins": []}
    cache_key = "coinmarketcap"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            params={"start": 1, "limit": 100, "convert": "USD"},
            headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"},
        )
        response.raise_for_status()
        rows = response.json().get("data", [])
        coins = []
        for row in rows:
            quote = (row.get("quote") or {}).get("USD") or {}
            coins.append(_normalise(
                row, "CoinMarketCap", quote.get("price"), quote.get("percent_change_24h"),
                quote.get("volume_24h"), quote.get("market_cap"), quote.get("last_updated"),
            ))
        return _save(cache_key, {"status": "ok", "source": "CoinMarketCap", "coins": coins})
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"status": "error", "source": "CoinMarketCap", "coins": [], "error": str(exc)[:180]}


async def _coinstats(client: httpx.AsyncClient, key: str) -> dict:
    if not key:
        return {"status": "not_configured", "source": "CoinStats", "coins": []}
    cache_key = "coinstats"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(
            "https://openapiv1.coinstats.app/coins",
            params={"currency": "USD", "limit": 100},
            headers={"X-API-KEY": key, "Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("result", payload.get("coins", [])) if isinstance(payload, dict) else payload
        coins = []
        for row in rows if isinstance(rows, list) else []:
            coins.append(_normalise(
                row, "CoinStats", row.get("price"), row.get("priceChange1d"),
                row.get("volume"), row.get("marketCap"), row.get("updatedAt"),
            ))
        return _save(cache_key, {"status": "ok", "source": "CoinStats", "coins": coins})
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"status": "error", "source": "CoinStats", "coins": [], "error": str(exc)[:180]}


async def _dia_bitcoin(client: httpx.AsyncClient) -> dict:
    cache_key = "dia-btc"
    cached = _cached(cache_key)
    if cached is not None:
        return cached
    # DIA's documented quotation endpoint needs a blockchain + asset address.
    # Bitcoin's native asset is represented by the zero address in DIA examples.
    url = "https://api.diadata.org/v1/assetQuotation/Bitcoin/0x0000000000000000000000000000000000000000"
    try:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        price = payload.get("Price") or payload.get("price")
        result = {
            "status": "ok" if price is not None else "unavailable",
            "source": "DIA",
            "asset": "BTC",
            "price_usd": float(price) if price is not None else None,
            "updated_at": payload.get("Time") or payload.get("time") or datetime.now(timezone.utc).isoformat(),
        }
        return _save(cache_key, result)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"status": "error", "source": "DIA", "asset": "BTC", "price_usd": None, "error": str(exc)[:180]}


async def get_crypto_market_overview() -> dict:
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout_seconds, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        gecko, cmc, stats, dia = await asyncio.gather(
            _coingecko(client, settings.coingecko_api_key),
            _coinmarketcap(client, settings.coinmarketcap_api_key),
            _coinstats(client, settings.coinstats_api_key),
            _dia_bitcoin(client),
        )
    providers = [gecko, cmc, stats]
    successful = [p for p in providers if p["status"] == "ok"]
    # Preserve each provider's own quote; do not silently average or blend different feeds.
    consensus: dict[str, dict] = {}
    for provider in successful:
        for coin in provider["coins"]:
            symbol = coin["symbol"]
            if not symbol:
                continue
            entry = consensus.setdefault(symbol, {"symbol": symbol, "name": coin["name"], "quotes": []})
            entry["quotes"].append({
                "source": coin["source"],
                "price_usd": coin["price_usd"],
                "change_24h_pct": coin["change_24h_pct"],
                "volume_24h_usd": coin["volume_24h_usd"],
                "market_cap_usd": coin["market_cap_usd"],
                "updated_at": coin["updated_at"],
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if successful else "unavailable",
        "providers": [
            {"name": p["source"], "status": p["status"], "assets_returned": len(p["coins"]), **({"error": p["error"]} if p.get("error") else {})}
            for p in providers
        ] + [{"name": "DIA", "status": dia["status"], "assets_returned": int(dia.get("price_usd") is not None), **({"error": dia["error"]} if dia.get("error") else {})}],
        "assets": list(consensus.values()),
        "dia_reference": dia,
        "notes": [
            "Each provider quote is kept separate; values are not averaged across different market methodologies.",
            "DIA integration currently provides a BTC reference quote only; broader token coverage requires DIA blockchain and asset addresses.",
            "Provider limits and update intervals depend on each account plan.",
        ],
    }
