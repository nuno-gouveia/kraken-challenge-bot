import copy

from src import notify, validate_alerts
from tests.conftest import NOW, read
from tests.test_heartbeat import assert_telegram_html


def test_seed_alerts_validate_clean(state):
    errors, warnings = validate_alerts.check(read(state, "alerts.json"), NOW)
    assert errors == []
    assert warnings == []


def test_validator_catches_what_would_break_the_heartbeat(state):
    doc = read(state, "alerts.json")
    doc["alerts"][0]["message"] = "SELL ALL now — really"
    doc["alerts"][1]["direction"] = "down"
    doc["alerts"][2]["on_done"] = {"arm": ["btc-nope"], "disarm": []}
    doc["alerts"][4]["level"] = 78230
    doc["alerts"].append({"id": "btc-entry", "pair": "XBTEUR", "direction": "above", "level": 77500, "kind": "action",
                          "message": "BUY $420 of BTC at market now.", "status": "armed",
                          "armed_at": "2026-10-03T07:00:00Z", "level_usd_ref": 87300})
    errors, warnings = validate_alerts.check(doc, NOW)
    assert "btc-exit: message has an em dash" in errors
    assert "btc-warning: direction must be below, above or time" in errors
    assert "btc-t1: on_done.arm names unknown alert btc-nope" in errors
    assert "btc-t2: EUR level 78230 is not a multiple of 50" in warnings
    assert "btc-entry: entry alert without a guard_band" in warnings


def test_notify_lists_alerts_and_changes(state):
    before = read(state, "alerts.json")
    after = copy.deepcopy(before)
    after["alerts"][0]["level"] = 72500
    after["alerts"] = [a for a in after["alerts"] if a["id"] != "btc-watch-high"]
    after["updated_by"] = "claude (daily brief)"
    text = notify.message(after, before, {"XBTEUR": 74550.1, "XBTUSD": 84000.0}, NOW, read(state, "account.json"))
    assert_telegram_html(text)
    assert text.startswith("<b>Alerts updated. Nothing to do now.</b> (13:00 Lisbon, by claude (daily brief))")
    assert "\nYou hold: 0.0049961 BTC, bought for $420.00.\n" in text
    assert "<b>You'll be told to act only if:</b>\n- BTC rises to EUR 78,200 / $88,113 (4.9% away): \"SELL" in text
    assert '- BTC falls to EUR 72,500 / $81,690 (2.7% away): "SELL ALL your BTC' in text
    assert "<b>Silent notes, nothing to do, if:</b>" in text
    assert "Changed: removed btc-watch-high; btc-exit moved from EUR 72,800 to EUR 72,500." in text
    assert text.endswith("Not financial advice.")


def test_notify_says_when_there_is_no_position(state):
    account = read(state, "account.json")
    account["positions"] = []
    text = notify.message(read(state, "alerts.json"), None, None, NOW, account)
    assert "\nYou hold no position, all cash ($630.00).\n" in text


def test_notify_skips_when_live_alerts_did_not_change(state, tmp_path, capsys):
    path = state / "alerts.json"
    assert notify.main(["--alerts", str(path), "--before", str(path), "--dry-run"]) == 0
    assert "unchanged" in capsys.readouterr().out
