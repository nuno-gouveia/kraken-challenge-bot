import pytest

from src import quiet_hours
from tests.conftest import T, FakeKraken
from tests.test_heartbeat import read, rearm, run, status

NIGHT = T("2026-10-03T02:15:40")  # 03:15 Lisbon
MORNING = T("2026-10-03T05:31:40")  # 06:31 Lisbon


@pytest.mark.parametrize("utc, quiet", [
    ("2026-10-02T21:29:59", False),  # 22:29 Lisbon (summer time, UTC+1)
    ("2026-10-02T21:30:00", True),   # 22:30
    ("2026-10-03T05:29:59", True),   # 06:29
    ("2026-10-03T05:30:00", False),  # 06:30
    ("2026-11-10T22:29:59", False),  # 22:29 Lisbon (winter time, UTC+0)
    ("2026-11-10T22:30:00", True),
    ("2026-11-11T06:29:59", True),
    ("2026-11-11T06:30:00", False),
])
def test_quiet_window_follows_lisbon_time(utc, quiet):
    assert quiet_hours.is_quiet(T(utc)) is quiet


def test_last_window_is_the_night_just_ended():
    window = (T("2026-10-02T21:30:00"), T("2026-10-03T05:30:00"))
    assert quiet_hours.last_window(MORNING) == window
    assert quiet_hours.last_window(T("2026-10-03T20:00:00")) == window
    assert quiet_hours.last_window(T("2026-11-11T07:00:00")) == (T("2026-11-10T22:30:00"), T("2026-11-11T06:30:00"))


def night_state(state):
    rearm(state, at="2026-10-02T21:00:00Z")


def test_action_due_at_night_is_held_not_sent(state):
    night_state(state)
    notifier, summary = run(state, FakeKraken("ohlc_1m_night.json"), now=NIGHT)
    assert "held btc-exit (quiet hours)" in summary
    # Only the watch alert goes out, and it is silent.
    assert [silent for _, silent in notifier.sent] == [True]
    assert "ACTION" not in notifier.sent[0][0]
    exit_alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert exit_alert["status"] == "held"
    assert exit_alert["held_first_touch_at"] == "2026-10-03T02:12:00Z"

    notifier, summary = run(state, FakeKraken("ohlc_1m_night.json"), now=NIGHT + 50)
    assert notifier.sent == [] and summary == []


def test_morning_recheck_price_recovered_no_action(state):
    night_state(state)
    run(state, FakeKraken("ohlc_1m_night.json"), now=NIGHT)
    notifier, summary = run(state, FakeKraken("ohlc_1m_morning_recovered.json"), now=MORNING)
    assert summary == ["morning update"]
    [(text, silent)] = notifier.sent
    assert silent is False
    assert text.startswith("<b>Morning update: actions held overnight")
    assert "first touched at 03:12; low overnight EUR 72,500." in text
    assert "Back above the level now: no action. The alert is armed again from 06:30" in text
    assert "Today's brief re-plans the day." in text
    exit_alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert exit_alert["status"] == "armed"
    assert exit_alert["armed_at"] == "2026-10-03T05:30:00Z"
    assert exit_alert["held_overnight"] == {"first_touch_at": "2026-10-03T02:12:00Z", "rechecked_at": "2026-10-03T05:30:00Z"}
    assert "held_at" not in exit_alert

    notifier, _ = run(state, FakeKraken("ohlc_1m_morning_recovered.json"), now=MORNING + 30)
    assert notifier.sent == []


def test_morning_recheck_still_through_sends_the_action(state):
    night_state(state)
    run(state, FakeKraken("ohlc_1m_night.json"), now=NIGHT)
    notifier, summary = run(state, FakeKraken("ohlc_1m_morning_still_below.json", ticker="ticker_low.json"), now=MORNING)
    assert summary == ["morning update", "fired btc-exit"]
    (morning, _), (action, silent) = notifier.sent
    assert "the action stands" in morning
    assert silent is False
    assert action.startswith("<b>ACTION: SELL ALL your BTC")
    assert "Held overnight: first touched at 03:12 (quiet hours), and still through the level at the 06:30 re-check." in action
    assert "ran late" not in action
    assert status(state)["btc-exit"] == "fired"


def test_touch_at_night_that_no_run_saw_is_rechecked_in_the_morning(state):
    # GitHub skipped every run overnight; the first run is at 06:31.
    night_state(state)
    notifier, summary = run(state, FakeKraken("ohlc_1m_morning_recovered.json"), now=MORNING)
    assert "morning update" in summary
    assert not any(t.startswith("<b>ACTION") for t, _ in notifier.sent)
    assert status(state)["btc-exit"] == "armed"


def test_system_messages_are_silent_at_night(state):
    night_state(state)
    session = FakeKraken()
    session.down = True
    sent = []
    for i in range(3):
        notifier, _ = run(state, session, now=NIGHT + i * 20)
        sent += notifier.sent
    [(text, silent)] = sent
    assert "NOT being watched" in text and silent is True
