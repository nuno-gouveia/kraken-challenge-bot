"""Technical indicators, standard definitions (as Kraken's and TradingView's charts use them).

- EMA: seeded with the simple average of the first n values, then
  alpha = 2 / (n + 1).
- RSI and ATR: Wilder's smoothing (first value a simple average, then
  avg = (prev * (n - 1) + x) / n).
- Bollinger: 20-period SMA +/- 2 population standard deviations.
- MACD: EMA12 - EMA26, signal EMA9 of MACD, histogram MACD - signal.

Every function takes oldest-first lists and returns the series aligned to
the input, None where there is not yet enough data.
"""

from __future__ import annotations

import math


def sma(values: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    for i in range(n - 1, len(values)):
        out[i] = sum(values[i - n + 1:i + 1]) / n
    return out


def ema(values: list[float | None], n: int) -> list[float | None]:
    """EMA of a series that may start with Nones (e.g. MACD before EMA26 exists)."""
    out: list[float | None] = [None] * len(values)
    start = next((i for i, v in enumerate(values) if v is not None), None)
    if start is None or len(values) - start < n:
        return out
    seed_end = start + n - 1
    prev = sum(values[start:seed_end + 1]) / n
    out[seed_end] = prev
    alpha = 2 / (n + 1)
    for i in range(seed_end + 1, len(values)):
        prev = values[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out


def _wilder(values: list[float], n: int, first_index: int) -> list[float | None]:
    """Wilder-smoothed series of `values`, whose first usable item is at first_index."""
    out: list[float | None] = [None] * (first_index + len(values))
    if len(values) < n:
        return out
    prev = sum(values[:n]) / n
    out[first_index + n - 1] = prev
    for i in range(n, len(values)):
        prev = (prev * (n - 1) + values[i]) / n
        out[first_index + i] = prev
    return out


def rsi(closes: list[float], n: int = 14) -> list[float | None]:
    if len(closes) < 2:
        return [None] * len(closes)
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = _wilder([max(c, 0.0) for c in changes], n, 1)
    losses = _wilder([max(-c, 0.0) for c in changes], n, 1)
    out: list[float | None] = []
    for g, l in zip(gains, losses):
        if g is None or l is None:
            out.append(None)
        elif l == 0:
            out.append(100.0 if g > 0 else 50.0)
        else:
            out.append(100 - 100 / (1 + g / l))
    return out


def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return tr


def atr(highs: list[float], lows: list[float], closes: list[float], n: int = 14) -> list[float | None]:
    # Wilder starts from the second bar, where a previous close exists.
    tr = true_range(highs, lows, closes)[1:]
    return _wilder(tr, n, 1)


def bollinger(closes: list[float], n: int = 20, k: float = 2.0):
    """(middle, upper, lower) series."""
    mid = sma(closes, n)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)
    for i, m in enumerate(mid):
        if m is None:
            continue
        window = closes[i - n + 1:i + 1]
        sd = math.sqrt(sum((x - m) ** 2 for x in window) / n)
        upper[i], lower[i] = m + k * sd, m - k * sd
    return mid, upper, lower


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
    """(macd, signal, histogram) series."""
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [f - s if f is not None and s is not None else None for f, s in zip(ef, es)]
    sig = ema(line, signal)
    hist = [m - s if m is not None and s is not None else None for m, s in zip(line, sig)]
    return line, sig, hist
