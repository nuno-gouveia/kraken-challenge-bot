import json

import pytest

from src import heartbeat, test_alert
from tests.conftest import NOW, T, FakeKraken, FakeNotifier, FakeResponse, read, write

EM_DASH = "\u2014"


def run(state, session=None, notifier=None, now=NOW, cmc_key=None, write_state=True):
    notifier = notifier or FakeNotifier()
    summary = heartbeat.run(
        state, notifier, session or FakeKraken(), cmc_key,
        now_fn=lambda: now, sleep=lambda _: None, write=write_state,
    )
    for text, _ in notifier.sent:
        assert EM_DASH not in text
        assert_telegram_html(text)
    return notifier, summary


def assert_telegram_html(text):
    """Telegram rejects the whole message on a stray '<' or '&' in HTML mode."""
    import re

    stripped = re.sub(r"</?b>", "", text)
    stripped = re.sub(r"&(lt|gt|amp|quot);", "", stripped)
    assert "<" not in stripped and ">" not in stripped and "&" not in stripped, text
    assert text.count("<b>") == text.count("</b>"), text


def rearm(state, at="2026-10-03T08:00:00Z", **changes):
    """Arm the seed alerts at a recent time, so only the 1-minute fixtures matter."""
    doc = read(state, "alerts.json")
    for a in doc["alerts"]:
        if a["status"] == "armed":
            a["armed_at"] = at
        a.update(changes.get(a["id"], {}))
    write(state, "alerts.json", doc)


def status(state):
    return {a["id"]: a["status"] for a in read(state, "alerts.json")["alerts"]}


def test_quiet_run_sends_nothing_and_writes_nothing(state):
    rearm(state)
    before = {p.name: p.read_text() for p in state.iterdir()}
    notifier, summary = run(state)
    assert notifier.sent == []
    assert summary == []
    assert {p.name: p.read_text() for p in state.iterdir()} == before


def test_wick_between_runs_fires_exit_and_warning_once(state):
    rearm(state)
    notifier, summary = run(state, FakeKraken("ohlc_1m_wick.json"))
    assert summary == ["fired btc-exit", "fired btc-warning"]
    (exit_text, exit_silent), (warn_text, warn_silent) = notifier.sent
    assert exit_silent is False and warn_silent is True
    assert exit_text.startswith("<b>ACTION: SELL ALL your BTC at market now.")
    assert "touched EUR 72,800 / $82,028 at 12:57 Lisbon; low since then EUR 72,760" in exit_text
    assert "Now: EUR 74,550 / $84,000 (Kraken, EUR/USD 1.1268 from XBTUSD/XBTEUR)" in exit_text
    assert "If you sell all now: about" in exit_text
    assert exit_text.endswith("Not financial advice.")
    assert "ACTION" not in warn_text
    s = status(state)
    assert s["btc-exit"] == s["btc-warning"] == "fired"
    assert s["btc-t1"] == "armed"
    exit_alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert exit_alert["fired_at"] == "2026-10-03T12:00:40Z" and exit_alert["fired_source"] == "kraken"

    # The next run sees the same wick and stays quiet.
    notifier, summary = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + 60)
    assert notifier.sent == [] and summary == []


def test_late_run_says_it_is_late_and_to_act_on_sight(state):
    rearm(state)
    notifier, _ = run(state, FakeKraken("ohlc_1m_late.json"))
    exit_text = notifier.sent[0][0]
    assert "at 12:40 Lisbon" in exit_text
    assert "first touched about 20 min ago (this check ran late)" in exit_text
    assert "Act at market on sight" in exit_text


def test_upside_spike_fires_t1_with_the_position(state):
    rearm(state)
    notifier, summary = run(state, FakeKraken("ohlc_1m_spike.json"))
    assert summary == ["fired btc-t1"]
    text = notifier.sent[0][0]
    assert text.startswith("<b>ACTION: SELL HALF your BTC")
    assert "high since then EUR 77,100" in text
    # 0.0049961 BTC at $84,000 = $419.67 against $420 paid.
    assert "Your BTC: 0.0049961 bought for $420.00, worth about $419.67 now (-$0.33)." in text
    assert "about -$1.59 after 0.3% slippage, balance about $1,048.41." in text
    assert status(state)["btc-t2"] == "armed"


def test_alert_older_than_twelve_hours_is_checked_on_fifteen_minute_candles(state):
    # Seed alerts were armed 2 Oct 18:47 UTC, before the 1-minute fixture starts.
    notifier, summary = run(state, FakeKraken("ohlc_1m_quiet.json"))
    assert "fired btc-exit" in summary
    text = notifier.sent[0][0]
    # 2 Oct 21:00 UTC candle (low 72,750). The 18:45 candle (low 72,650) holds
    # trades from before the alert existed and must not count.
    assert "at 2 Oct 22:00 to 2 Oct 22:15 Lisbon; low since then EUR 72,750" in text


def test_touch_before_valid_from_is_reported_once_and_stays_armed(state):
    rearm(state, **{"btc-exit": {"valid_from": "2026-10-03T11:58:00Z"}})
    notifier, summary = run(state, FakeKraken("ohlc_1m_wick.json"))
    gate = [t for t, silent in notifier.sent if "NOT authorised" in t]
    assert len(gate) == 1
    assert "from 12:58 Lisbon time" in gate[0]
    assert status(state)["btc-exit"] == "armed"
    assert "btc-exit touched outside its window" in summary

    notifier, _ = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + 60)
    assert notifier.sent == []


def test_touch_after_valid_until_is_not_authorised(state):
    rearm(state, **{"btc-exit": {"valid_until": "2026-10-03T11:00:00Z"}})
    notifier, _ = run(state, FakeKraken("ohlc_1m_late.json"))
    assert any("NOT authorised" in t for t, _ in notifier.sent)
    assert status(state)["btc-exit"] == "armed"


def test_touch_inside_window_fires(state):
    rearm(state, **{"btc-exit": {"valid_from": "2026-10-03T11:50:00Z", "valid_until": "2026-10-04T00:00:00Z"}})
    _, summary = run(state, FakeKraken("ohlc_1m_wick.json"))
    assert "fired btc-exit" in summary


def test_entry_alert_carries_the_guard_band(state):
    rearm(state)
    doc = read(state, "alerts.json")
    doc["alerts"].append({
        "id": "btc-breakout-entry", "pair": "XBTEUR", "direction": "above", "level": 77000,
        "kind": "action", "message": "BUY $420 of BTC at market (breakout entry).", "status": "armed",
        "armed_at": "2026-10-03T08:00:00Z", "guard_band": [77000, 77400],
    })
    write(state, "alerts.json", doc)
    notifier, _ = run(state, FakeKraken("ohlc_1m_spike.json"))
    text = next(t for t, _ in notifier.sent if "breakout" in t)
    assert "Only buy if Kraken shows between EUR 77,000 and EUR 77,400 ($86,760 to $87,211)." in text
    assert "Below EUR 77,000 do NOT buy." in text
    assert "Right now the price is OUTSIDE that band: do NOT buy." in text


def test_price_outage_alerts_after_three_runs_and_once_on_recovery(state):
    rearm(state)
    session = FakeKraken()
    session.down = True
    for i in range(5):
        notifier, _ = run(state, session, now=NOW + i * 20)
        if i == 2:
            assert len(notifier.sent) == 1 and "NOT being watched" in notifier.sent[0][0]
        else:
            assert notifier.sent == []
    assert read(state, "heartbeat.json")["price_failures"] == 3

    session.down = False
    notifier, summary = run(state, session)
    assert [t.startswith("<b>Back online.</b>") for t, _ in notifier.sent] == [True]
    assert read(state, "heartbeat.json") == {"price_failures": 0, "outage_notified": False, "alerts_problems": []}

    notifier, _ = run(state, session)
    assert notifier.sent == []


class KrakenDownCmcUp(FakeKraken):
    def __init__(self, eur, usd):
        super().__init__()
        self.prices = {"EUR": eur, "USD": usd}

    def get(self, url, params=None, timeout=None, headers=None):
        if "coinmarketcap" in url:
            assert headers["X-CMC_PRO_API_KEY"] == "cmc-key"
            price = self.prices[params["convert"]]
            return FakeResponse({"data": {"BTC": [{"quote": {params["convert"]: {"price": price}}}]}})
        return FakeResponse({"error": ["EService:Unavailable"], "result": {}})


def test_coinmarketcap_fallback_fires_and_is_labelled(state):
    rearm(state)
    notifier, summary = run(state, KrakenDownCmcUp(72700.0, 81900.0), cmc_key="cmc-key")
    assert "fired btc-exit" in summary
    text = notifier.sent[0][0]
    assert "FALLBACK price from CoinMarketCap, not Kraken" in text
    alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert alert["fired_source"] == "cmc"
    assert read(state, "heartbeat.json")["price_failures"] == 0


def test_telegram_failure_keeps_the_alert_armed_for_the_next_run(state):
    rearm(state)
    notifier, summary = run(state, FakeKraken("ohlc_1m_wick.json"), notifier=FakeNotifier(ok=False))
    assert notifier.failed and summary == []
    assert status(state)["btc-exit"] == "armed"
    _, summary = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + 60)
    assert "fired btc-exit" in summary


def test_bad_alert_is_reported_once_and_others_still_watched(state):
    rearm(state, **{"btc-t1": {"direction": "beloww"}})
    notifier, _ = run(state, FakeKraken("ohlc_1m_wick.json"))
    problems = [t for t, _ in notifier.sent if "Problem with the alerts file" in t]
    assert len(problems) == 1 and "btc-t1: direction must be below, above or time" in problems[0]
    assert status(state)["btc-exit"] == "fired"

    notifier, _ = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + 60)
    assert notifier.sent == []

    rearm(state, **{"btc-t1": {"direction": "above"}})
    notifier, _ = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + 90)
    assert [t for t, _ in notifier.sent] == ["<b>The alerts file is fixed.</b> All armed alerts are being watched again."]


def test_unreadable_alerts_file_is_reported(state):
    (state / "alerts.json").write_text("{ not json")
    notifier, _ = run(state)
    assert "alerts.json can't be read" in notifier.sent[0][0]
    assert (state / "alerts.json").read_text() == "{ not json"


def test_missing_armed_at_is_stamped_now(state):
    rearm(state, **{"btc-t2": {"armed_at": None}})
    run(state)
    t2 = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-t2")
    assert t2["armed_at"] == "2026-10-03T12:00:40Z"


def test_dry_run_writes_nothing(state):
    rearm(state)
    before = (state / "alerts.json").read_text()
    notifier, summary = run(state, FakeKraken("ohlc_1m_wick.json"), write_state=False)
    assert len(notifier.sent) == 2 and summary
    assert (state / "alerts.json").read_text() == before
    assert json.loads(before)


@pytest.mark.parametrize("armed, fires", [("2026-10-03T11:50:00Z", True), ("2026-10-03T11:58:00Z", False)])
def test_acceptance_test_alert_fires_exactly_once(state, armed, fires):
    """SPEC.md milestone 1: a test alert 0.1% from the price fires exactly once."""
    doc = read(state, "alerts.json")
    doc["alerts"] = []
    price_at_arming = 74580.0
    alert = test_alert.build(price_at_arming, 1.1268, "below", 0.1, "watch", T(armed))
    assert alert["level"] == 74505
    doc["alerts"].append(alert)
    write(state, "alerts.json", doc)

    sent = []
    for i in range(4):
        notifier, _ = run(state, FakeKraken("ohlc_1m_wick.json"), now=NOW + i * 20)
        sent += notifier.sent
    assert len(sent) == (1 if fires else 0)
    if fires:
        assert sent[0][0].startswith("<b>TEST alert, nothing to do.")
        assert status(state)[alert["id"]] == "fired"


def test_main_refuses_to_run_without_telegram_secrets(monkeypatch, state):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("HEARTBEAT_DRY_RUN", raising=False)
    assert heartbeat.main(["--state-dir", str(state)]) == 2
