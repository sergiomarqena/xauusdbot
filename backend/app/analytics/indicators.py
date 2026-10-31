from collections.abc import Sequence


def ema(values: Sequence[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for index in range(period, len(values)):
        previous = alpha * values[index] + (1.0 - alpha) * previous
        result[index] = previous
    return result


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def value(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        rs = gain / loss
        return 100.0 - (100.0 / (1.0 + rs))

    result[period] = value(avg_gain, avg_loss)
    for index in range(period + 1, len(values)):
        delta_index = index - 1
        avg_gain = ((avg_gain * (period - 1)) + gains[delta_index]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[delta_index]) / period
        result[index] = value(avg_gain, avg_loss)
    return result


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("period must be positive")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("high, low and close arrays must have the same length")
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    true_ranges = [highs[0] - lows[0]]
    for index in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    current = sum(true_ranges[1 : period + 1]) / period
    result[period] = current
    for index in range(period + 1, len(closes)):
        current = ((current * (period - 1)) + true_ranges[index]) / period
        result[index] = current
    return result


def indicator_summary(candles: Sequence) -> dict:
    closes = [float(candle.close) for candle in candles]
    highs = [float(candle.high) for candle in candles]
    lows = [float(candle.low) for candle in candles]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)

    def latest(values):
        return next((item for item in reversed(values) if item is not None), None)

    close = closes[-1] if closes else None
    previous = closes[-2] if len(closes) > 1 else None
    return {
        "last_close": close,
        "change_percent": ((close / previous) - 1.0) * 100.0 if previous else None,
        "ema_20": latest(ema20),
        "ema_50": latest(ema50),
        "rsi_14": latest(rsi14),
        "atr_14": latest(atr14),
        "observations": len(closes),
    }
