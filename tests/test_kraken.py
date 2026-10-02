import pytest

from src import kraken
from tests.conftest import NOW, T, FakeKraken, fixture


def test_ticker_maps_internal_pair_names():
    last = kraken.ticker_last(FakeKraken(), ["XBTEUR", "XBTUSD"])
    assert last == {"XBTEUR": 74550.1, "XBTUSD": 84000.0}


def test_ohlc_parses_string_prices_in_time_order():
    candles = kraken.parse_ohlc(fixture("ohlc_1m_wick.json")["result"], "XBTEUR", 60)
    assert candles[0].time == T("2026-10-03T06:00:00")
    assert candles[-1].time == T("2026-10-03T12:00:00")  # the open candle is kept
    wick = next(c for c in candles if c.time == T("2026-10-03T11:57:00"))
    assert wick.low == 72760.0


def test_stale_response_is_rejected():
    candles = kraken.parse_ohlc(fixture("ohlc_1m_stale.json")["result"], "XBTEUR", 60)
    with pytest.raises(kraken.KrakenError, match="stale"):
        kraken.check_fresh(candles, NOW)


def test_kraken_error_field_raises():
    class ErrorSession(FakeKraken):
        def get(self, url, params=None, timeout=None, headers=None):
            from tests.conftest import FakeResponse

            return FakeResponse({"error": ["EService:Unavailable"]})

    with pytest.raises(kraken.KrakenError, match="EService:Unavailable"):
        kraken.ticker_last(ErrorSession(), ["XBTEUR"])


def test_market_retries_once_after_a_stale_window():
    session = FakeKraken(one_min="ohlc_1m_stale.json")
    sleeps = []

    def fixed_after_sleep(s):
        sleeps.append(s)
        session.one_min = "ohlc_1m_quiet.json"

    m = kraken.fetch_market_with_retry(
        session, ["XBTEUR"], {"XBTEUR": int(T("2026-10-03T10:00:00"))}, now_fn=lambda: NOW, sleep=fixed_after_sleep
    )
    assert sleeps == [5]
    assert m.candles["XBTEUR"][-1].time == T("2026-10-03T12:00:00")
    assert m.eur_usd == pytest.approx(84000.0 / 74550.1)


def test_fifteen_minute_candles_fill_only_the_gap_before_the_one_minute_window():
    session = FakeKraken()
    m = kraken.fetch_market(session, ["XBTEUR"], {"XBTEUR": int(T("2026-10-02T18:47:00"))}, NOW)
    candles = m.candles["XBTEUR"]
    coarse = [c for c in candles if c.interval_s == 900]
    fine = [c for c in candles if c.interval_s == 60]
    assert coarse and fine
    assert coarse[-1].time < fine[0].time
    assert [c.time for c in candles] == sorted(c.time for c in candles)


def test_no_fifteen_minute_fetch_when_one_minute_window_covers_the_alert():
    session = FakeKraken()
    kraken.fetch_market(session, ["XBTEUR"], {"XBTEUR": int(T("2026-10-03T10:00:00"))}, NOW)
    assert [p["interval"] for u, p in session.calls if u.endswith("OHLC")] == [1]
