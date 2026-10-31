from app.analytics.indicators import atr, ema, rsi


def test_ema_seed_and_length():
    values = ema([1, 2, 3, 4, 5], 3)
    assert len(values) == 5
    assert values[1] is None
    assert values[2] == 2
    assert values[3] is not None


def test_rsi_monotonic_increase():
    values = rsi(list(range(1, 20)), 14)
    assert values[14] == 100.0


def test_atr_constant_range():
    highs = [11.0] * 20
    lows = [9.0] * 20
    closes = [10.0] * 20
    values = atr(highs, lows, closes, 14)
    assert values[14] == 2.0


def test_mismatched_atr_input_rejected():
    try:
        atr([2.0], [1.0, 0.5], [1.5])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("Expected a ValueError")


def test_candle_rejects_invalid_ohlc():
    from app.domain.models import Candle
    from pydantic import ValidationError
    from datetime import datetime, timezone

    try:
        Candle(timestamp=datetime.now(timezone.utc), open=10, high=9, low=8, close=8.5)
    except ValidationError:
        return
    raise AssertionError("Invalid OHLC relationship was accepted")
