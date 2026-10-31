from datetime import datetime, timedelta, timezone

from app.domain.models import Candle
from app.services.terminal import _build_sentiment, _score_headline, _bias_from_candles, _volume_flow


def candle_series(start: float, step: float, count: int = 90, direction_volume: float = 10.0):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    items = []
    for index in range(count):
        close = start + step * index
        open_price = close - step * 0.35
        items.append(Candle(
            timestamp=base + timedelta(hours=index),
            open=open_price,
            high=max(open_price, close) + 0.8,
            low=min(open_price, close) - 0.8,
            close=close,
            volume=direction_volume,
        ))
    return items


def test_headline_keywords_tag_dovish_as_gold_supportive():
    item = _score_headline({
        "title": "Central bank officials signal a dovish tone and discuss rate cuts",
        "summary": "",
        "source": "test",
    })
    assert item["headline_tone"] == "GOLD SUPPORTIVE"
    assert item["tone_score"] > 0


def test_headline_keywords_tag_hawkish_as_gold_headwind():
    item = _score_headline({
        "title": "Officials remain hawkish and signal rates higher for longer",
        "summary": "",
        "source": "test",
    })
    assert item["headline_tone"] == "GOLD HEADWIND"
    assert item["tone_score"] < 0


def test_sentiment_exposes_counts_and_disclaimer():
    result = _build_sentiment([
        {"title": "Dovish rate cut talk", "summary": "", "source": "test"},
        {"title": "Hawkish higher for longer policy", "summary": "", "source": "test"},
        {"title": "Quarterly statistical report released", "summary": "", "source": "test"},
    ])
    assert result["supportive_count"] == 1
    assert result["headwind_count"] == 1
    assert result["neutral_count"] == 1
    assert "not a causal market model" in result["disclaimer"]


def test_bias_classifier_detects_uptrend_without_calling_it_probability():
    row = _bias_from_candles("BTC", "1D", candle_series(100, 0.5), "test feed")
    assert row["bias"] == "BULLISH"
    assert "not a probability" in row["basis"]


def test_bias_classifier_detects_downtrend():
    row = _bias_from_candles("BTC", "4H", candle_series(200, -0.5), "test feed")
    assert row["bias"] == "BEARISH"


def test_volume_flow_is_explicitly_a_candle_proxy():
    candles = candle_series(100, 0.5, count=30)
    flow = _volume_flow("XAU", candles, "test feed", "Up/down candle volume proxy")
    assert flow["status"] == "ok"
    assert flow["buy_total"] > 0
    assert flow["sell_total"] == 0
    assert "proxy" in flow["method"]
