import math

import pytest

from src import indicators as ind
from src import snapshot
from tests.conftest import NOW, FakeResponse

DAY, HOUR = 86400, 3600


def rows(start, step, n, base, wobble):
    out = []
    for i in range(n):
        p = base * (1 + wobble * math.sin(i / 5) + 0.0005 * i)
        out.append([start + i * step, f"{p:.8g}", f"{p * 1.01:.8g}", f"{p * 0.99:.8g}", f"{p * 1.002:.8g}", "0", "1", 1])
    return out


class FakeKrakenMarket:
    """Daily (720) and hourly (720) candles for every pair, ending in the open candle."""

    BASES = {"XBTUSD": 84000, "XBTEUR": 74550, "ETHUSD": 2500, "ETHEUR": 2220, "LINKUSD": 15, "LINKEUR": 13.3,
             "BCHUSD": 400, "BCHEUR": 355, "XDGUSD": 0.12, "XDGEUR": 0.106, "SHIBUSD": 0.0000125, "SHIBEUR": 0.0000111}

    def __init__(self, missing=()):
        self.missing = set(missing)
        self.calls = 0

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls += 1
        pair, interval = params["pair"], int(params["interval"])
        if pair in self.missing:
            return FakeResponse({"error": ["EQuery:Unknown asset pair"]})
        step = interval * 60
        last_open = int(NOW) - int(NOW) % step
        body = rows(last_open - 719 * step, step, 720, self.BASES[pair], 0.03)
        return FakeResponse({"error": [], "result": {pair: body, "last": body[-2][0]}})


def build(**kw):
    return snapshot.build(FakeKrakenMarket(**kw), NOW, sleep=lambda _: None)


def test_snapshot_has_every_asset_in_both_currencies():
    snap = build()
    assert snap["fetched_at"] == "2026-10-03T12:00:40Z" and snap["errors"] == []
    assert set(snap["assets"]) == {"BTC", "ETH", "LINK", "BCH", "DOGE", "SHIB"}
    for asset in snap["assets"].values():
        assert set(asset) == {"USD", "EUR"}
    btc = snap["assets"]["BTC"]["USD"]
    assert btc["pair"] == "XBTUSD"
    d = btc["daily"]
    for key in ("rsi14", "atr14", "atr14_pct", "ema20", "ema50", "ema200"):
        assert d[key] is not None
    assert d["last_closed_date"] == "2026-10-02" and btc["open_candle"]["date"] == "2026-10-03"
    assert snap["eur_usd"] == pytest.approx(btc["last"] / snap["assets"]["BTC"]["EUR"]["last"], rel=1e-4)
    assert snap["assets"]["SHIB"]["USD"]["last"] < 0.001  # tiny prices keep their digits


def test_indicators_ignore_the_open_candle():
    m = FakeKrakenMarket()
    daily = snapshot.kraken.parse_ohlc(m.get("", {"pair": "XBTUSD", "interval": 1440}).json()["result"], "XBTUSD", DAY)
    hourly = snapshot.kraken.parse_ohlc(m.get("", {"pair": "XBTUSD", "interval": 60}).json()["result"], "XBTUSD", HOUR)
    a = snapshot.analyse(daily, hourly)
    crashed = daily[:-1] + [daily[-1].__class__(daily[-1].time, 1, 1, 1, 1, DAY)]
    b = snapshot.analyse(crashed, hourly)
    assert a["daily"] == b["daily"]
    closes = [c.close for c in daily[:-1]]
    assert a["daily"]["rsi14"] == round(ind.rsi(closes)[-1], 2)


def test_a_missing_pair_is_reported_not_fatal():
    snap = build(missing={"SHIBEUR"})
    assert snap["errors"] == ["SHIBEUR: OHLC: EQuery:Unknown asset pair"]
    assert "EUR" not in snap["assets"]["SHIB"] and "USD" in snap["assets"]["SHIB"]


def test_without_btc_the_job_fails():
    snap = build(missing={"XBTEUR"})
    assert snap["eur_usd"] is None
