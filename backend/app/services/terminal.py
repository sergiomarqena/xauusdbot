from __future__ import annotations

import asyncio
import csv
import html
import io
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_SECONDS = {"macro": 900, "crypto": 60, "news": 300}
FRED_SERIES = {
    "broad_usd": ("DTWEXBGS", "Broad trade-weighted USD index", "index"),
    "us10y": ("DGS10", "US 10Y nominal Treasury yield", "%"),
    "real10y": ("DFII10", "US 10Y inflation-adjusted yield", "%"),
    "wti": ("DCOILWTICO", "WTI crude oil", "USD/barrel"),
}
RSS_FEEDS = [
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("US Bureau of Labor Statistics", "https://www.bls.gov/feed/bls_latest.rss"),
]
BINANCE_SYMBOLS = ["BTCUSDT", "ETHUSDT"]


def _cache_get(key: str):
    item = _CACHE.get(key)
    if item and item[0] > time.monotonic():
        return item[1]
    return None


def _cache_set(key: str, value: Any, ttl: int):
    _CACHE[key] = (time.monotonic() + ttl, value)
    return value


async def _fred_series(client: httpx.AsyncClient, key: str, series_id: str, label: str, units: str) -> dict:
    cache_key = f"fred:{series_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": series_id},
        )
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.text)))
        valid = [row for row in rows if row.get(series_id) not in (None, "", ".")]
        if not valid:
            raise ValueError("No observations in source response")
        latest = valid[-1]
        previous = valid[-2] if len(valid) > 1 else None
        result = {
            "key": key,
            "label": label,
            "series_id": series_id,
            "value": float(latest[series_id]),
            "previous": float(previous[series_id]) if previous else None,
            "change": (
                float(latest[series_id]) - float(previous[series_id])
                if previous else None
            ),
            "observed_at": latest.get("observation_date"),
            "units": units,
            "source": "Federal Reserve Bank of St. Louis (FRED)",
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "status": "ok",
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        result = {
            "key": key, "label": label, "series_id": series_id,
            "value": None, "previous": None, "change": None,
            "observed_at": None, "units": units,
            "source": "FRED", "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "status": "unavailable", "error": str(exc)[:180],
        }
    return _cache_set(cache_key, result, CACHE_SECONDS["macro"])


async def _crypto_ticker(client: httpx.AsyncClient, symbol: str) -> dict:
    cache_key = f"binance:{symbol}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(
            "https://data-api.binance.vision/api/v3/ticker/24hr",
            params={"symbol": symbol},
        )
        response.raise_for_status()
        row = response.json()
        result = {
            "symbol": symbol,
            "last_price": float(row["lastPrice"]),
            "change_percent": float(row["priceChangePercent"]),
            "quote_volume": float(row["quoteVolume"]),
            "as_of": datetime.fromtimestamp(
                float(row["closeTime"]) / 1000, tz=timezone.utc
            ).isoformat(),
            "source": "Binance public spot market data",
            "status": "ok",
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        result = {
            "symbol": symbol, "last_price": None, "change_percent": None,
            "quote_volume": None, "as_of": None,
            "source": "Binance public spot market data",
            "status": "unavailable", "error": str(exc)[:180],
        }
    return _cache_set(cache_key, result, CACHE_SECONDS["crypto"])


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


async def _rss_feed(client: httpx.AsyncClient, source: str, url: str) -> list[dict]:
    cache_key = f"rss:{source}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        response = await client.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = _clean_text(item.findtext("title"))
            link = (item.findtext("link") or "").strip()
            published_raw = item.findtext("pubDate") or ""
            description = _clean_text(item.findtext("description"))
            try:
                published = parsedate_to_datetime(published_raw).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError, OverflowError):
                published = published_raw or None
            if title and link.startswith("https://"):
                items.append({
                    "source": source, "title": title, "url": link,
                    "published_at": published, "summary": description[:240],
                })
        result = items
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        result = [{
            "source": source, "title": "Feed temporarily unavailable",
            "url": url, "published_at": None, "summary": str(exc)[:180],
        }]
    return _cache_set(cache_key, result, CACHE_SECONDS["news"])


async def build_terminal_snapshot() -> dict:
    timeout = httpx.Timeout(10.0, connect=5.0)
    headers = {"User-Agent": "NORDXAU-GPT/0.2 (+market-research-dashboard)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        macro_tasks = [
            _fred_series(client, key, series_id, label, units)
            for key, (series_id, label, units) in FRED_SERIES.items()
        ]
        crypto_tasks = [_crypto_ticker(client, symbol) for symbol in BINANCE_SYMBOLS]
        news_tasks = [_rss_feed(client, source, url) for source, url in RSS_FEEDS]
        macro, crypto, news = await asyncio.gather(
            asyncio.gather(*macro_tasks),
            asyncio.gather(*crypto_tasks),
            asyncio.gather(*news_tasks),
        )

    headlines = [item for feed in news for item in feed]
    headlines.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "macro": list(macro),
        "crypto": list(crypto),
        "news": headlines[:12],
        "feeds": [
            {"name": source, "status": "ok" if news[index] and news[index][0].get("title") != "Feed temporarily unavailable" else "unavailable"}
            for index, (source, _) in enumerate(RSS_FEEDS)
        ],
        "notes": [
            "Broad USD is a trade-weighted dollar index proxy, not the ICE DXY contract.",
            "FRED macro observations update on their own publication schedules and may be delayed.",
            "Crypto cards show 24-hour public spot-market statistics.",
            "News is syndicated from official Federal Reserve and BLS RSS feeds; headlines are not trade instructions.",
        ],
    }
