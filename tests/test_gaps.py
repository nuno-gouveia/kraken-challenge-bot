"""The first run after GitHub didn't run the heartbeat tells Nuno about the gap."""

import json

import requests

from src import gaps, heartbeat
from tests.conftest import NOW, T, FakeKraken, FakeNotifier, FakeResponse
from tests.test_heartbeat import assert_telegram_html, rearm, status

NIGHT = T("2026-10-03T02:15:40")  # 03:15 Lisbon


def gap_texts(notifier):
    return [(t, silent) for t, silent in notifier.sent if t.startswith("<b>Checks were down")]


def test_no_notice_after_a_normal_five_minute_interval(state):
    rearm(state)
    notifier, summary = run_with_gap(state, minutes=6)
    assert gap_texts(notifier) == [] and summary == []


def test_gap_with_nothing_touched_says_so_once(state):
    rearm(state)
    notifier, summary = run_with_gap(state, minutes=50)
    [(text, silent)] = gap_texts(notifier)
    assert silent is False
    assert text.startswith("<b>Checks were down from 12:10 to 13:00 Lisbon.</b> GitHub did not run me")
    assert "nothing touched any of your alerts. Nothing to do." in text
    assert summary == ["gap notice"]


def test_gap_with_a_touch_points_to_the_alert_sent_first(state):
    rearm(state)
    notifier, summary = run_with_gap(state, minutes=50, session=FakeKraken("ohlc_1m_wick.json"))
    assert summary == ["fired btc-exit", "fired btc-warning", "gap notice"]
    assert notifier.sent[0][0].startswith("<b>ACTION: SELL ALL")
    [(text, _)] = gap_texts(notifier)
    assert "Alerts touched in it are in the messages just before this one" in text
    assert status(state)["btc-exit"] == "fired"


def test_gap_while_prices_are_down_says_the_window_is_not_checked_yet(state):
    rearm(state)
    session = FakeKraken()
    session.down = True
    notifier, _ = run_with_gap(state, minutes=50, session=session)
    [(text, _)] = gap_texts(notifier)
    assert "that window is not checked yet" in text


def test_gap_with_no_alerts_armed(state):
    doc_path = state / "alerts.json"
    doc = json.loads(doc_path.read_text())
    for a in doc["alerts"]:
        a["status"] = "disabled"
    doc_path.write_text(json.dumps(doc))
    notifier, _ = run_with_gap(state, minutes=50)
    [(text, _)] = gap_texts(notifier)
    assert "No price alerts were armed, so nothing was missed." in text


def test_gap_notice_is_silent_in_quiet_hours(state):
    rearm(state, at="2026-10-03T01:00:00Z")
    notifier, _ = run_with_gap(state, minutes=50, now=NIGHT, session=FakeKraken("ohlc_1m_night.json"))
    [(_, silent)] = gap_texts(notifier)
    assert silent is True


def run_with_gap(state, minutes, now=NOW, session=None):
    notifier = FakeNotifier()
    summary = heartbeat.run(state, notifier, session or FakeKraken(), None, now_fn=lambda: now,
                            sleep=lambda _: None, last_ok=now - minutes * 60)
    for text, _ in notifier.sent:
        assert "\u2014" not in text
        assert_telegram_html(text)
    return notifier, summary


class FakeGitHub:
    def __init__(self, body=None, error=None):
        self.body, self.error, self.calls = body, error, []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        if self.error:
            raise self.error
        return FakeResponse(self.body)


def test_last_success_is_the_newest_success_other_than_this_run():
    gh = FakeGitHub({"workflow_runs": [
        {"id": 870, "conclusion": None, "updated_at": "2026-10-06T09:25:40Z"},  # this run, in progress
        {"id": 869, "conclusion": "success", "updated_at": "2026-10-06T09:20:47Z"},
        {"id": 868, "conclusion": "cancelled", "updated_at": "2026-10-06T09:21:00Z"},
        {"id": 700, "conclusion": "success", "updated_at": "2026-10-06T02:00:00Z"},
    ]})
    assert gaps.last_success_end(gh, "owner/repo", "tok", "870") == T("2026-10-06T09:20:47")
    url, params, headers = gh.calls[0]
    assert url.endswith("/repos/owner/repo/actions/workflows/heartbeat.yml/runs")
    assert "status" not in params  # the status-filtered list lags behind


def test_no_recent_success_means_unknown_not_a_gap():
    gh = FakeGitHub({"workflow_runs": [{"id": 5, "conclusion": "failure", "updated_at": "2026-10-06T09:20:47Z"}]})
    assert gaps.last_success_end(gh, "o/r", "tok", "6") is None


def test_last_success_unknown_when_github_fails(capsys):
    assert gaps.last_success_end(FakeGitHub(error=requests.ConnectionError("x")), "o/r", "tok", "1") is None
    assert "tok" not in capsys.readouterr().out


def test_a_gap_is_reported_once_even_if_github_keeps_returning_the_same_old_run(state):
    rearm(state)
    old_success = NOW - 7 * 3600
    for i in range(3):
        notifier = FakeNotifier()
        heartbeat.run(state, notifier, FakeKraken(), None, now_fn=lambda: NOW + i * 300,
                      sleep=lambda _: None, last_ok=old_success)
        assert len(gap_texts(notifier)) == (1 if i == 0 else 0)


def test_a_new_gap_after_one_was_reported_is_reported(state):
    rearm(state)
    run_with_gap(state, minutes=50)
    notifier = FakeNotifier()
    later = NOW + 3 * 3600
    heartbeat.run(state, notifier, FakeKraken(), None, now_fn=lambda: later, sleep=lambda _: None,
                  last_ok=later - 40 * 60)
    assert len(gap_texts(notifier)) == 1
