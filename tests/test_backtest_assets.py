"""The multi-asset backtest (src/backtest_assets.py) on hand-made trades and candles."""

from src import backtest_active as ba
from src import backtest_assets as bx
from tests.test_backtest_active import market


def ev(t_in, t_out, net=0.01, stop=0.04, asset="A"):
    return bx.Ev(t_in, t_out, net, mae=-0.01, mfe=0.02, stop=stop, asset=asset)


def test_one_position_at_a_time_across_assets():
    kept = bx.one_at_a_time([ev(100, 200, asset="A"), ev(150, 180, asset="B"), ev(200, 300, asset="B")])
    assert [(e.t_in, e.asset) for e in kept] == [(100, "A"), (200, "B")]


def test_buying_on_another_assets_signal_uses_this_assets_prices():
    flat, up = [(100, 100, 100)] * 6, [(103, 100, 103)] * 4
    mk = market(flat + up, (2026, 3, 2, 10, 0))
    [e] = bx.events(mk, ba.Rule(6, 0.04, target=0.02, stop=0.04), at=[2])
    assert e.t_in == mk.bars[3].t and abs(e.net - (0.02 - ba.SLIP)) < 1e-9 and e.stop == 0.04


def test_row_counts_profit_in_units_of_the_planned_risk():
    evs = [ev(i * 86400 * 30, i * 86400 * 30 + 3600, net=0.0215, stop=0.04) for i in range(12)]
    text = bx.row("x", evs, years=1.0)
    assert "| 12 | 100% | +2.15% | +6.0 |" in text   # 12 x 2.15% / 4.3%
