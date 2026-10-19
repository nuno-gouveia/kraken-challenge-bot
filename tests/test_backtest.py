"""The backtest engine on hand-made candles."""

from src import backtest as bt

H = 3600


def bars(prices, step=900, t0=1_700_000_000):
    """(high, low, close) per bar; open = previous close."""
    out, prev = [], prices[0][2]
    for i, (h, l, c) in enumerate(prices):
        out.append(bt.Bar(t0 + i * step, prev, h, l, c))
        prev = c
    return out


def test_rolling_high():
    b = bars([(1, 0, 1), (5, 0, 1), (3, 0, 1), (2, 0, 1), (1, 0, 1)])
    assert bt.rolling_high(b, 2) == [1, 5, 5, 3, 2]


def test_flash_dip_buys_after_the_drop_and_sells_at_the_target():
    flat = [(100, 100, 100)] * 8
    drop = [(100, 95, 95)]  # 5% under the 1h high
    after = [(95, 95, 95), (96.5, 95, 96)] + [(96, 96, 96)] * 10
    p = bt.Flash(window_h=1, drop=0.04, target=0.015, stop=0.03, hold_h=24, delay_bars=1)
    [tr] = bt.flash_dip(bars(flat + drop + after), p)
    assert tr.entry == 95 and tr.why == "target"
    assert abs(tr.gross - 0.015) < 1e-9
    assert abs(tr.net - (0.015 - 2 * bt.FEE - bt.EXIT_SLIP)) < 1e-9


def test_flash_dip_stop_wins_a_bar_that_touches_both():
    seq = [(100, 100, 100)] * 8 + [(100, 95, 95), (95, 95, 95), (99, 90, 95)] + [(95, 95, 95)] * 4
    p = bt.Flash(1, 0.04, 0.015, 0.03, 24, 1)
    [tr] = bt.flash_dip(bars(seq), p)
    assert tr.why == "stop" and abs(tr.gross + 0.03) < 1e-9


def test_flash_dip_time_exit():
    seq = [(100, 100, 100)] * 8 + [(100, 95, 95), (95, 95, 95)] + [(95.5, 94.5, 95.2)] * (24 * 4 + 5)
    [tr] = bt.flash_dip(bars(seq), bt.Flash(1, 0.04, 0.03, 0.03, 24, 1))
    assert tr.why == "time" and tr.exit_t - tr.entry_t == 24 * H


def test_score_sizes_by_risk_and_records_the_pass():
    tr = bt.Trade(0, 1, 100, 0.20, 0.03, "target")  # +20% gross on a 3% stop
    s = bt.Score("x", [tr]).run()
    size = min(bt.START * bt.RISK / 0.03, bt.START * bt.CAP)  # $420 cap binds
    assert abs(s.balance - (bt.START + size * tr.net)) < 1e-6
    assert s.passed_at == 1 and s.failed_at is None


def test_rsi_and_atr_need_fourteen_days():
    d = bars([(100 + i, 99 + i, 100 + i) for i in range(20)], step=86400)
    rsi, atr = bt.rsi_atr(d)
    assert rsi[13] is None and rsi[14] == 100.0 and abs(atr[14] - atr[19]) < 1e-9
