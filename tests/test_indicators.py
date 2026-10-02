import pytest

from src import indicators as ind

# Wilder's RSI reference series, as published in StockCharts' RSI article
# (ChartSchool, "Relative Strength Index"); first RSI at the 15th close.
CLOSES = [44.3389, 44.0902, 44.1497, 43.6124, 44.2779, 44.8264, 45.0955, 45.4245, 45.8433, 46.0826,
          45.8931, 46.0328, 45.6140, 46.2820, 46.2820, 46.0028, 46.0328, 46.4116, 46.2222, 45.6439,
          46.2122, 46.2521, 45.7137, 46.4515, 45.7835, 45.3548, 44.0288, 44.1783, 44.2181, 44.5672,
          43.4205, 42.6628, 43.1314]
RSI = [70.53, 66.32, 66.55, 69.41, 66.36, 57.97, 62.93, 63.26, 56.06, 62.38, 54.71, 50.42, 39.99,
       41.46, 41.87, 45.46, 37.30, 33.08, 37.77]


def test_rsi_matches_the_wilder_reference():
    out = ind.rsi(CLOSES, 14)
    assert out[:14] == [None] * 14
    assert [round(x, 2) for x in out[14:]] == RSI


def test_rsi_edges():
    assert ind.rsi(list(range(1, 30)), 14)[-1] == 100.0
    assert ind.rsi([5.0] * 30, 14)[-1] == 50.0


def test_ema_seeds_with_sma_then_smooths():
    out = ind.ema([1, 2, 3, 4, 5], 3)
    assert out[:2] == [None, None]
    assert out[2] == 2.0  # (1 + 2 + 3) / 3
    assert out[3] == pytest.approx(3.0)  # 4 * 0.5 + 2 * 0.5
    assert out[4] == pytest.approx(4.0)
    assert ind.ema([7.5] * 300, 200)[-1] == pytest.approx(7.5)


def test_atr_uses_true_range_and_wilder():
    highs = [10, 12, 11, 15]
    lows = [8, 9, 9, 10]
    closes = [9, 11, 10, 14]
    # TR from bar 2: max(3, 3, 0) = 3; max(2, 0, 2) = 2; max(5, 5, 0) = 5
    out = ind.atr(highs, lows, closes, 2)
    assert out == [None, None, 2.5, (2.5 + 5) / 2]


def test_bollinger_population_sd():
    mid, up, lo = ind.bollinger([2, 4, 4, 4, 5, 5, 7, 9], 8, 2)
    # mean 5, population sd 2
    assert (mid[-1], up[-1], lo[-1]) == (5.0, 9.0, 1.0)
    assert ind.bollinger([3.0] * 25)[1][-1] == 3.0


def test_macd_of_a_flat_series_is_zero_and_aligned():
    line, sig, hist = ind.macd([100.0] * 60)
    assert line[24] is None and line[25] == pytest.approx(0)
    assert sig[33] == pytest.approx(0) and sig[32] is None
    assert hist[-1] == pytest.approx(0)


def test_macd_of_a_rising_series_is_positive():
    line, sig, hist = ind.macd([float(i) for i in range(100)])
    assert line[-1] > 0 and sig[-1] > 0
    assert line[-1] == pytest.approx(7.0, abs=0.01)  # EMA lag difference for a slope of 1: (26-12)/2
