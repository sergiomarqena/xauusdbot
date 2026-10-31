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

from app.analytics.indicators import indicator_summary
from app.config import get_settings
from app.data.twelvedata import TwelveDataError, TwelveDataProvider
from app.domain.models import Candle

_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_SECONDS = {"macro": 900, "crypto": 45, "news": 300, "candles": 90}
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
BIAS_TIMEFRAMES = [
    ("1H", "1h", "1h", "1h"),
    ("4H", "4h", "4h", "4h"),
    ("1D", "1day", "1d", "1d"),
    ("1W", "1week", "1w", "1wk"),
]
INTERVALS = {"15min": "15m", "1h": "1h", "4h": "4h", "1day": "1d", "1week": "1w"}


def _cache_get(key: str):
    item = _CACHE.get(key)
    if item and item[0] > time.monotonic():
        return item[1]
    return None


def _cache_set(key: str, value: Any, ttl: int):
    _CACHE[key] = (time.monotonic() + ttl, value)
    return value


def _score_headline(item: dict) -> dict:
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    supportive = (
        "dovish", "rate cut", "rate cuts", "cuts rates", "cut rates",
        "lower rates", "yields fall", "yield falls", "yield decline",
        "cooling inflation", "softer inflation", "weak jobs", "weak labor",
        "geopolitical", "safe haven", "safe-haven", "risk-off",
        "war escalat", "tensions rise",
    )
    headwind = (
        "hawkish", "rate hike", "rate hikes", "hikes rates", "higher for longer",
        "yields rise", "yield rises", "yield climb", "hot inflation",
        "strong jobs", "strong labor", "dollar strengthens", "strong dollar",
        "tightening", "rate increase",
    )
    positive_hits = [term for term in supportive if term in text]
    negative_hits = [term for term in headwind if term in text]
    # This is a transparent keyword tagger, not an AI interpretation or a price forecast.
    score = max(-3, min(3, len(positive_hits) - len(negative_hits)))
    if score > 0:
        tone = "GOLD SUPPORTIVE"
    elif score < 0:
        tone = "GOLD HEADWIND"
    else:
        tone = "NEUTRAL / UNCLEAR"
    return {
        **item,
        "headline_tone": tone,
        "tone_score": score,
        "matched_terms": positive_hits + negative_hits,
    }


def _build_sentiment(headlines: list[dict]) -> dict:
    scored = [_score_headline(item) for item in headlines]
    supportive = [x for x in scored if x["tone_score"] > 0]
    headwind = [x for x in scored if x["tone_score"] < 0]
    neutral = [x for x in scored if x["tone_score"] == 0]
    support_weight = sum(x["tone_score"] for x in supportive)
    headwind_weight = sum(abs(x["tone_score"]) for x in headwind)
    total_weight = support_weight + headwind_weight
    return {
        "method": "Transparent keyword tagging of headline and short summary text",
        "supportive_count": len(supportive),
        "headwind_count": len(headwind),
        "neutral_count": len(neutral),
        "supportive_weight": support_weight,
        "headwind_weight": headwind_weight,
        "supportive_fill": round(100 * support_weight / total_weight) if total_weight else 0,
        "headwind_fill": round(100 * headwind_weight / total_weight) if total_weight else 0,
        "dominant": (
            "GOLD SUPPORTIVE" if support_weight > headwind_weight
            else "GOLD HEADWIND" if headwind_weight > support_weight
            else "BALANCED / NO CLEAR READ"
        ),
        "headlines": scored,
        "disclaimer": "Headline tone is a keyword-based context tag, not a causal market model or trading signal. Hawkish/dovish effects depend on expectations and what is already priced in.",
    }


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
            "key": key, "label": label, "series_id": series_id,
            "value": float(latest[series_id]),
            "previous": float(previous[series_id]) if previous else None,
            "change": float(latest[series_id]) - float(previous[series_id]) if previous else None,
            "observed_at": latest.get("observation_date"), "units": units,
            "source": "Federal Reserve Bank of St. Louis (FRED)",
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "status": "ok",
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        result = {
            "key": key, "label": label, "series_id": series_id,
            "value": None, "previous": None, "change": None, "observed_at": None,
            "units": units, "source": "FRED",
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
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
            "as_of": datetime.fromtimestamp(float(row["closeTime"]) / 1000, tz=timezone.utc).isoformat(),
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


def _bias_from_candles(asset: str, timeframe: str, candles: list[Candle], source: str) -> dict:
    if len(candles) < 55:
        return {
            "asset": asset, "timeframe": timeframe, "bias": "UNAVAILABLE",
            "alignment": None, "last_price": candles[-1].close if candles else None,
            "source": source, "reason": "At least 55 bars are required for stable EMA 50 context.",
        }
    measures = indicator_summary(candles)
    close = float(candles[-1].close)
    ema20 = measures.get("ema_20")
    ema50 = measures.get("ema_50")
    rsi14 = measures.get("rsi_14")
    atr14 = measures.get("atr_14") or 0.0
    if ema20 is None or ema50 is None or rsi14 is None:
        bias = "UNAVAILABLE"
        alignment = None
    else:
        bullish = close > ema20 and ema20 > ema50 and rsi14 >= 52
        bearish = close < ema20 and ema20 < ema50 and rsi14 <= 48
        if bullish:
            bias = "BULLISH"
        elif bearish:
            bias = "BEARISH"
        else:
            bias = "MIXED"
        distance = (close - ema50) / atr14 if atr14 else 0.0
        alignment = round(max(0, min(100, 50 + distance * 8 + (rsi14 - 50) * 0.65)))
    return {
        "asset": asset, "timeframe": timeframe, "bias": bias,
        "alignment": alignment, "last_price": close,
        "ema20": ema20, "ema50": ema50, "rsi14": rsi14,
        "source": source,
        "basis": "Close vs EMA 20/50 structure and RSI 14. Alignment is not a probability.",
        "bars": len(candles),
    }


def _volume_flow(
    asset: str,
    candles: list[Candle],
    source: str,
    method: str,
    taker_values: list[tuple[float, float]] | None = None,
    quote_unit: str = "quote volume",
) -> dict:
    if not candles:
        return {
            "asset": asset, "status": "unavailable", "method": method,
            "source": source, "unit": quote_unit, "points": [],
            "reason": "No source candles returned.",
        }
    points = []
    for index, candle in enumerate(candles[-24:]):
        if taker_values is not None:
            buy, sell = taker_values[-len(candles[-24:]) + len(points)]
        elif candle.volume is not None and candle.volume > 0:
            # Directional candle-volume proxy only; not exchange or institutional capital flow.
            volume = float(candle.volume) * float(candle.close)
            buy = volume if candle.close >= candle.open else 0.0
            sell = volume if candle.close < candle.open else 0.0
        else:
            continue
        points.append({
            "time": candle.timestamp.isoformat(),
            "buy": round(float(buy), 4),
            "sell": round(float(sell), 4),
        })
    if not points:
        return {
            "asset": asset, "status": "unavailable", "method": method,
            "source": source, "unit": quote_unit, "points": [],
            "reason": "Source does not provide usable volume for this instrument.",
        }
    return {
        "asset": asset, "status": "ok", "method": method,
        "source": source, "unit": quote_unit, "points": points,
        "buy_total": round(sum(x["buy"] for x in points), 2),
        "sell_total": round(sum(x["sell"] for x in points), 2),
    }


async def _binance_klines(client: httpx.AsyncClient, symbol: str, interval: str, limit: int = 200) -> tuple[list[Candle], list[tuple[float, float]]]:
    key = f"binance-klines:{symbol}:{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    response = await client.get(
        "https://data-api.binance.vision/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    response.raise_for_status()
    rows = response.json()
    candles: list[Candle] = []
    flow: list[tuple[float, float]] = []
    for row in rows:
        timestamp = datetime.fromtimestamp(float(row[0]) / 1000, tz=timezone.utc)
        candles.append(Candle(
            timestamp=timestamp, open=float(row[1]), high=float(row[2]),
            low=float(row[3]), close=float(row[4]), volume=float(row[5]),
        ))
        total_quote = float(row[7])
        taker_buy_quote = float(row[10])
        flow.append((taker_buy_quote, max(0.0, total_quote - taker_buy_quote)))
    value = (candles, flow)
    return _cache_set(key, value, CACHE_SECONDS["candles"])


async def _twelvedata_candles(interval: str, limit: int = 200) -> list[Candle]:
    settings = get_settings()
    if not settings.twelve_data_api_key:
        return []
    key = f"twelvedata:XAU/USD:{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    provider = TwelveDataProvider(settings.twelve_data_api_key, settings.request_timeout_seconds)
    candles = await provider.get_candles(settings.default_symbol, interval, limit)
    return _cache_set(key, candles, CACHE_SECONDS["candles"])


async def _yahoo_oil_candles(interval: str, limit: int = 200) -> list[Candle]:
    if interval == "1h":
        source_interval, date_range = "1h", "1mo"
    elif interval == "4h":
        source_interval, date_range = "1h", "3mo"
    elif interval == "15min":
        source_interval, date_range = "15m", "5d"
    elif interval == "1day":
        source_interval, date_range = "1d", "6mo"
    else:
        source_interval, date_range = "1wk", "2y"
    key = f"yahoo-oil:CL=F:{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), headers={"User-Agent": "Mozilla/5.0 NORDXAU.GPT"}) as client:
        response = await client.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/CL=F",
            params={"range": date_range, "interval": source_interval, "events": "history"},
        )
        response.raise_for_status()
        payload = response.json()
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise ValueError("Yahoo Finance returned no WTI futures series.")
    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = item.get("indicators", {}).get("quote", [{}])[0]
    opens, highs, lows, closes, volumes = (
        quote.get("open", []), quote.get("high", []), quote.get("low", []),
        quote.get("close", []), quote.get("volume", []),
    )
    candles = []
    for i, stamp in enumerate(timestamps):
        try:
            if any(values[i] is None for values in (opens, highs, lows, closes)):
                continue
            candles.append(Candle(
                timestamp=datetime.fromtimestamp(stamp, tz=timezone.utc),
                open=float(opens[i]), high=float(highs[i]), low=float(lows[i]),
                close=float(closes[i]),
                volume=float(volumes[i]) if i < len(volumes) and volumes[i] is not None else None,
            ))
        except (ValueError, TypeError, IndexError):
            continue
    candles.sort(key=lambda x: x.timestamp)
    if interval == "4h":
        grouped: dict[datetime, list[Candle]] = {}
        for candle in candles:
            bucket = candle.timestamp.replace(hour=(candle.timestamp.hour // 4) * 4, minute=0, second=0, microsecond=0)
            grouped.setdefault(bucket, []).append(candle)
        candles = [
            Candle(
                timestamp=stamp, open=bars[0].open, high=max(x.high for x in bars),
                low=min(x.low for x in bars), close=bars[-1].close,
                volume=sum(x.volume or 0 for x in bars) if any(x.volume is not None for x in bars) else None,
            )
            for stamp, bars in sorted(grouped.items())
        ]
    if not candles:
        raise ValueError("Yahoo Finance returned no usable WTI futures candles.")
    return _cache_set(key, candles[-limit:], CACHE_SECONDS["candles"])


async def _safe_bias(asset: str, label: str, interval: str, fetcher, source: str) -> tuple[dict, list[Candle]]:
    try:
        candles = await fetcher(interval)
        return _bias_from_candles(asset, label, candles, source), candles
    except (httpx.HTTPError, TwelveDataError, ValueError, KeyError, TypeError) as exc:
        return ({
            "asset": asset, "timeframe": label, "bias": "UNAVAILABLE",
            "alignment": None, "last_price": None, "source": source,
            "reason": str(exc)[:180],
        }, [])


async def _asset_bias_and_flow(selected_interval: str, selected_gold: list[Candle] | None) -> tuple[list[dict], list[dict]]:
    timeout = httpx.Timeout(10.0, connect=5.0)
    headers = {"User-Agent": "NORDXAU-GPT/0.3"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        tasks = []
        for label, xau_interval, btc_interval, oil_interval in BIAS_TIMEFRAMES:
            tasks.append(_safe_bias(
                "BTC", label, btc_interval,
                lambda i, c=client: _btc_candles(c, i),
                "Binance BTC/USDT spot",
            ))
            if selected_gold is not None and xau_interval == selected_interval:
                tasks.append(asyncio.sleep(0, result=(
                    _bias_from_candles("XAU", label, selected_gold, "Twelve Data XAU/USD"),
                    selected_gold,
                )))
            else:
                tasks.append(_safe_bias(
                    "XAU", label, xau_interval,
                    lambda i: _twelvedata_candles(i, 200),
                    "Twelve Data XAU/USD",
                ))
            tasks.append(_safe_bias(
                "OIL", label, oil_interval,
                lambda i: _yahoo_oil_candles(i, 200),
                "Yahoo Finance WTI futures (CL=F)",
            ))
        raw = await asyncio.gather(*tasks)
        # tasks are inserted BTC, XAU, OIL for each timeframe.
        bias_rows = [entry[0] for entry in raw]
        chosen_btc = await _safe_binance_flow(client, "BTCUSDT", INTERVALS.get(selected_interval, "1h"))
        chosen_xau = selected_gold or []
        chosen_oil = []
        try:
            chosen_oil = await _yahoo_oil_candles(selected_interval if selected_interval in ("15min", "1h", "4h", "1day", "1week") else "1h", 24)
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            pass
        flow_rows = [
            chosen_btc,
            _volume_flow("XAU", chosen_xau, "Twelve Data XAU/USD", "Up/down candle volume proxy; not consolidated global gold flows", quote_unit="provider volume × price"),
            _volume_flow("OIL", chosen_oil, "Yahoo Finance CL=F futures", "Up/down futures-candle volume proxy; not global crude capital flows", quote_unit="contracts × price"),
        ]
    return bias_rows, flow_rows


async def _btc_candles(client: httpx.AsyncClient, interval: str) -> list[Candle]:
    candles, _ = await _binance_klines(client, "BTCUSDT", interval, 200)
    return candles


async def _safe_binance_flow(client: httpx.AsyncClient, symbol: str, interval: str) -> dict:
    try:
        candles, flow = await _binance_klines(client, symbol, interval, 200)
        return _volume_flow(
            "BTC", candles, "Binance BTC/USDT spot",
            "Taker-buy quote volume vs taker-sell quote-volume estimate",
            taker_values=flow, quote_unit="USDT quote volume",
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        return {
            "asset": "BTC", "status": "unavailable",
            "method": "Binance taker-buy / taker-sell quote volume",
            "source": "Binance BTC/USDT spot", "unit": "USDT quote volume",
            "points": [], "reason": str(exc)[:180],
        }


async def build_terminal_snapshot(
    selected_interval: str = "1h",
    selected_gold: list[Candle] | None = None,
) -> dict:
    timeout = httpx.Timeout(10.0, connect=5.0)
    headers = {"User-Agent": "NORDXAU-GPT/0.3 (+market-research-dashboard)"}
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
    sentiment = _build_sentiment(headlines)
    bias, flow = await _asset_bias_and_flow(selected_interval, selected_gold)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "macro": list(macro),
        "crypto": list(crypto),
        "news": sentiment["headlines"][:12],
        "sentiment": {key: value for key, value in sentiment.items() if key != "headlines"},
        "bias": bias,
        "flow": flow,
        "feeds": [
            {"name": source, "status": "ok" if news[index] and news[index][0].get("title") != "Feed temporarily unavailable" else "unavailable"}
            for index, (source, _) in enumerate(RSS_FEEDS)
        ],
        "notes": [
            "Broad USD is a trade-weighted dollar index proxy, not the ICE DXY contract.",
            "FRED macro observations update on their own publication schedules and may be delayed.",
            "Crypto cards show 24-hour public spot-market statistics.",
            "News tone is keyword-tagged context only, not a model forecast.",
            "BTC flow uses taker-side quote volume; XAU and OIL use candle-volume direction proxies where source volume exists.",
            "Flow proxies are not net exchange deposits, institutional flows, or consolidated global market flows.",
        ],
    }
