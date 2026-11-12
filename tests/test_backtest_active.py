"""The stricter backtest (quiet hours, the floor inside a trade) on hand-made candles."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src import backtest as bt
from src import backtest_active as ba

LISBON = ZoneInfo("Europe/Lisbon")


def market(prices, start):
    """(high, low, close) per 15-minute candle from `start` (Lisbon time); open = previous close."""
    t0 = int(datetime(*start, tzinfo=LISBON).timestamp())
    out, prev = [], prices[0][2]
    for i, (h, l, c) in enumerate(prices):
        out.append(bt.Bar(t0 + i * 900, prev, h, l, c))
        prev = c
    return ba.Market("TEST", out, [bt.quiet(b.t) for b in out])


def test_a_stop_hit_at_night_is_sold_at_the_0630_price():
    # bought at 22:30; the price falls to 90 overnight and is 92 when Nuno wakes up
    night = [(100, 90, 91)] + [(92, 91, 92)] * 31   # the candles that open from 22:30 to 06:15
    mk = market([(100, 100, 100)] + night + [(93, 92, 93)] * 4, (2026, 3, 2, 22, 15))
    assert mk.asleep[:2] == [False, True] and mk.asleep[32:34] == [True, False]
    t = ba.one_trade(mk, 0, target=0.02, stop=0.04, hold=96, slip=0.003)
    assert t.why == "stop at 06:30"
    assert abs(t.net - (92 / 100 - 1 - 0.003)) < 1e-9   # not the -4% stop: the price at 06:30
    assert abs(t.mae - (-0.10)) < 1e-9                  # the floor check sees the night's low


def test_a_target_touched_at_night_and_lost_again_is_not_a_sale():
    night = [(103, 100, 100)] * 32
    mk = market([(100, 100, 100)] + night + [(100, 100, 100)] * 3 + [(102.5, 100, 102)] * 2, (2026, 3, 2, 22, 15))
    t = ba.one_trade(mk, 0, target=0.02, stop=0.04, hold=96, slip=0.003)
    assert t.why == "target" and t.m == 36   # the first candle that reaches +2% in awake hours


def test_cushion_sizing_shrinks_after_a_loss_and_never_exceeds_the_balance():
    size = ba.cushion(0.35)
    assert abs(size(1050.60, 0.04) - 0.35 * 100.60 / 0.043) < 1e-6
    assert size(1010.0, 0.04) < size(1050.60, 0.04)
    assert ba.cushion(0.9)(1050.60, 0.04) == 1050.60


def test_a_run_fails_when_equity_touches_the_floor_inside_a_trade():
    mk = market([(100, 100, 100)] * 4, (2026, 3, 2, 10, 0))
    mk.bars[-1].t = mk.bars[0].t + 2 * ba.YEAR_S   # room for one weekly start with a year ahead
    deep = [ba.Trade(0, 1, net=0.017, mae=-0.10, mfe=0.02, why="target")]
    assert ba.challenge(mk, deep, ba.fixed(1.0), 0.04).failed > 0
    assert ba.challenge(mk, deep, ba.fixed(0.4), 0.04).failed == 0
