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


def test_last_success_skips_this_run():
    gh = FakeGitHub({"workflow_runs": [
        {"id": 710, "updated_at": "2026-10-05T20:26:00Z"},
        {"id": 709, "updated_at": "2026-10-05T20:21:34Z"},
    ]})
    assert gaps.last_success_end(gh, "owner/repo", "tok", "710") == T("2026-10-05T20:21:34")
    url, params, headers = gh.calls[0]
    assert url.endswith("/repos/owner/repo/actions/workflows/heartbeat.yml/runs")
    assert params["status"] == "success"


def test_last_success_unknown_when_github_fails(capsys):
    assert gaps.last_success_end(FakeGitHub(error=requests.ConnectionError("x")), "o/r", "tok", "1") is None
    assert "tok" not in capsys.readouterr().out
