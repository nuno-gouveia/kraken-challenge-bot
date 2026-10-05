"""Time alerts: fire at a set time (`at`) instead of on a price level."""

import copy

from src import notify, validate_alerts
from tests.conftest import NOW, T, FakeKraken, FakeNotifier, read, write
from tests.test_heartbeat import assert_telegram_html, rearm, run, status
from tests.test_inbound import msg, press

NIGHT = T("2026-10-03T22:05:00")  # 23:05 Lisbon
MORNING = T("2026-10-04T05:31:40")  # 06:31 Lisbon


def timed(aid="btc-cpi", at="2026-10-03T11:58:00Z", kind="action", **extra):
    a = {
        "id": aid, "pair": "XBTEUR", "direction": "time", "at": at, "level": None, "kind": kind,
        "message": "SELL ALL your BTC at market now. US CPI prints at 14:30 Lisbon." if kind == "action"
        else "Tomorrow is CPI. Nothing to do now.",
        "status": "armed", "armed_at": "2026-10-03T08:00:00Z",
        "valid_from": None, "valid_until": None, "guard_band": None,
        "on_done": {"arm": [], "disarm": ["btc-exit", "btc-warning", "btc-t1", "btc-t2"]} if kind == "action" else None,
    }
    a.update(extra)
    return a


def add(state, *new, price_alerts=True):
    rearm(state)
    doc = read(state, "alerts.json")
    if not price_alerts:
        for a in doc["alerts"]:
            a["status"] = "disabled"
    doc["alerts"] += list(new)
    write(state, "alerts.json", doc)


def alert(state, aid):
    return next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == aid)


def test_due_time_action_fires_once_with_buttons_price_and_position(state):
    add(state, timed())
    notifier, summary = run(state)
    assert summary == ["fired btc-cpi"]
    [(text, silent)] = notifier.sent
    assert silent is False and notifier.markups[0]["inline_keyboard"][0][0]["callback_data"] == "done:btc-cpi"
    assert text.startswith("<b>ACTION: SELL ALL your BTC at market now. US CPI prints at 14:30 Lisbon.</b>")
    assert "Scheduled for 12:58 Lisbon. (Alert btc-cpi)" in text
    assert "ran late" not in text
    assert "Now: EUR 74,550 / $84,000 (Kraken, EUR/USD 1.1268 from XBTUSD/XBTEUR)." in text
    assert "If you sell all now: about" in text
    assert "Tap Done once you've sold, or send /sold all at &lt;price&gt;." in text
    assert text.endswith("Not financial advice.")
    a = alert(state, "btc-cpi")
    assert a["status"] == "fired" and a["fired_at"] == "2026-10-03T12:00:40Z" and a["fired_source"] == "kraken"

    notifier, summary = run(state, now=NOW + 300)
    assert notifier.sent == [] and summary == []


def test_time_alert_not_due_sends_nothing_and_writes_nothing(state):
    add(state, timed(at="2026-10-14T09:00:00Z"))
    before = {p.name: p.read_text() for p in state.iterdir()}
    notifier, summary = run(state)
    assert notifier.sent == [] and summary == []
    assert {p.name: p.read_text() for p in state.iterdir()} == before


def test_time_alert_alone_does_not_fetch_prices_until_due(state):
    add(state, timed(at="2026-10-14T09:00:00Z"), price_alerts=False)
    session = FakeKraken()
    run(state, session)
    assert session.calls == []


def test_time_alert_goes_out_even_when_prices_are_down(state):
    add(state, timed(), price_alerts=False)
    session = FakeKraken()
    session.down = True
    notifier, summary = run(state, session)
    assert summary == ["fired btc-cpi"]
    text = notifier.sent[0][0]
    assert "I can't read prices right now: check the price in the Kraken app." in text
    assert alert(state, "btc-cpi")["fired_source"] == "clock"


def test_late_time_alert_says_so(state):
    add(state, timed(at="2026-10-03T11:00:00Z"))
    notifier, _ = run(state)
    assert "Note: this is 60 min after the scheduled time (quiet hours, or this check ran late)." in notifier.sent[0][0]


def test_time_action_due_in_quiet_hours_waits_for_the_morning(state):
    add(state, timed(at="2026-10-03T22:00:00Z"), price_alerts=False)
    session = FakeKraken()
    notifier, summary = run(state, session, now=NIGHT)
    assert notifier.sent == [] and summary == [] and session.calls == []
    assert status(state)["btc-cpi"] == "armed"

    notifier, summary = run(state, FakeKraken("ohlc_1m_morning_recovered.json"), now=MORNING)
    assert summary == ["fired btc-cpi"]
    assert "Scheduled for 3 Oct 23:00 Lisbon." in notifier.sent[0][0]
    assert "min after the scheduled time" in notifier.sent[0][0]


def test_time_watch_alert_goes_out_silently_at_night(state):
    add(state, timed("btc-cpi-eve", at="2026-10-03T22:00:00Z", kind="watch"), price_alerts=False)
    notifier, summary = run(state, now=NIGHT)
    assert summary == ["fired btc-cpi-eve"]
    [(text, silent)] = notifier.sent
    assert silent is True and "ACTION" not in text and notifier.markups[0] is None
    assert text.startswith("<b>Tomorrow is CPI. Nothing to do now.</b>")


def test_done_on_a_time_alert_applies_its_on_done(state):
    add(state, timed())
    run(state)
    notifier = FakeNotifier(updates=[press(6, "done:btc-cpi")])
    run(state, notifier=notifier, now=NOW + 60)
    s = status(state)
    assert s["btc-cpi"] == "done"
    assert s["btc-exit"] == s["btc-warning"] == s["btc-t1"] == s["btc-t2"] == "disabled"
    assert "/sold all at &lt;price&gt;" in notifier.sent[0][0]


def test_closing_the_position_disarms_a_pending_time_sell(state):
    add(state, timed(at="2026-10-14T09:00:00Z"))
    run(state, notifier=FakeNotifier(updates=[msg(5, "sold all at 85000")]))
    assert status(state)["btc-cpi"] == "disabled"


def test_t1_done_disarms_the_time_exit_through_on_done(state):
    add(state, timed(at="2026-10-14T09:00:00Z"))
    doc = read(state, "alerts.json")
    t1 = next(a for a in doc["alerts"] if a["id"] == "btc-t1")
    t1["on_done"]["disarm"].append("btc-cpi")
    t1.update(status="fired", fired_at="2026-10-03T11:57:30Z", fired_source="kraken")
    write(state, "alerts.json", doc)
    run(state, notifier=FakeNotifier(updates=[msg(5, "/sold half at 86817")]))
    s = status(state)
    assert s["btc-t1"] == "done" and s["btc-cpi"] == "disabled" and s["btc-breakeven"] == "armed"


def test_alerts_listing_shows_time_alerts_after_price_alerts(state):
    add(state, timed(at="2026-10-14T09:00:00Z"))
    notifier = FakeNotifier(updates=[msg(2, "/alerts")])
    notifier, _ = run(state, notifier=notifier)
    text = notifier.sent[0][0]
    assert text.startswith("<b>Watching 7 alerts</b>")
    lines = text.splitlines()
    assert lines[-2] == "- at 14 Oct 10:00 Lisbon: ACTION, SELL ALL your BTC at market now. US CPI prints at 14:30 Lisbon."


def test_notify_lists_time_alerts_and_moves(state):
    before = read(state, "alerts.json")
    before["alerts"].append(timed(at="2026-10-14T09:00:00Z"))
    after = copy.deepcopy(before)
    after["alerts"][-1]["at"] = "2026-10-14T08:00:00Z"
    text = notify.message(after, before, {"XBTEUR": 74550.1, "XBTUSD": 84000.0}, NOW)
    assert_telegram_html(text)
    assert '- it is 14 Oct 09:00 Lisbon: "SELL ALL your BTC at market now.' in text
    assert "btc-cpi moved from at 14 Oct 10:00 Lisbon to at 14 Oct 09:00 Lisbon" in text


def test_validator_on_time_alerts(state):
    doc = read(state, "alerts.json")
    doc["alerts"] += [
        timed("t-ok", at="2026-10-14T09:00:00Z"),
        timed("t-no-at", at=None),
        timed("t-bad-at", at="next tuesday"),
        timed("t-night", at="2026-10-13T23:00:00Z"),
        timed("t-past", at="2026-10-01T09:00:00Z"),
    ]
    errors, warnings = validate_alerts.check(doc, NOW)
    assert "t-no-at: a time alert needs `at`" in errors
    assert "t-bad-at: at is not an ISO time" in errors
    assert not any(e.startswith("t-ok") for e in errors + warnings)
    assert "t-night: at falls in quiet hours (22:30 to 06:30 Lisbon), it waits until 06:30" in warnings
    assert "t-past: at is in the past, it fires on the next heartbeat" in warnings
