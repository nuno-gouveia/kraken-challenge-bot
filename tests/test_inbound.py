import json

import pytest

from src import account as acct
from src import commands
from tests.conftest import NOW, FakeKraken, FakeNotifier, read, write
from tests.test_heartbeat import rearm, run, status

CHAT = 4242


def msg(uid, text, chat=CHAT):
    return {"update_id": uid, "message": {"message_id": uid, "date": int(NOW) - 30, "chat": {"id": chat}, "text": text}}


def press(uid, data, chat=CHAT):
    return {"update_id": uid, "callback_query": {
        "id": f"cb{uid}", "data": data, "message": {"message_id": 77, "date": int(NOW) - 60, "chat": {"id": chat}}}}


def inbox(state):
    return [json.loads(line) for line in (state / "inbox.jsonl").read_text().splitlines() if line.strip()]


def fire(state, *ids):
    doc = read(state, "alerts.json")
    for a in doc["alerts"]:
        if a["id"] in ids:
            a.update(status="fired", fired_at="2026-10-03T11:57:30Z", fired_source="kraken")
    write(state, "alerts.json", doc)


def reply_to(state, *updates, **kw):
    rearm(state)
    notifier = FakeNotifier(updates=list(updates))
    notifier, summary = run(state, notifier=notifier, **kw)
    return notifier, summary


# ---- parsing ---------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Bought 420$ at 84065$", {"cmd": "bought", "asset": "BTC", "usd": 420.0, "price": 84065.0, "price_ccy": "USD"}),
    ("/bought 420 at 84,065", {"cmd": "bought", "asset": "BTC", "usd": 420.0, "price": 84065.0, "price_ccy": "USD"}),
    ("bought $100 of eth at 2510.5", {"cmd": "bought", "asset": "ETH", "usd": 100.0, "price": 2510.5, "price_ccy": "USD"}),
    ("/bought@KrakenBot 100 at 74600 eur", {"cmd": "bought", "asset": "BTC", "usd": 100.0, "price": 74600.0, "price_ccy": "EUR"}),
    ("sold all at 82150", {"cmd": "sold", "asset": "BTC", "amount": "all", "price": 82150.0, "price_ccy": "USD"}),
    ("Sold half at €77,050.", {"cmd": "sold", "asset": "BTC", "amount": "half", "price": 77050.0, "price_ccy": "EUR"}),
    ("/sold 200 at 86800", {"cmd": "sold", "asset": "BTC", "amount": 200.0, "price": 86800.0, "price_ccy": "USD"}),
    ("sold the rest at 88000", {"cmd": "sold", "asset": "BTC", "amount": "all", "price": 88000.0, "price_ccy": "USD"}),
    ("/status", {"cmd": "status"}),
    ("alerts", {"cmd": "alerts"}),
    ("/start", {"cmd": "help"}),
    ("what do you think of ETH?", {"cmd": "unknown"}),
])
def test_parse(text, expected):
    assert commands.parse(text) == {"dry": False, **expected}


def test_parse_dry_run_and_unknown_asset():
    assert commands.parse("/dryrun Bought 100 at 84000")["dry"] is True
    assert commands.parse("/dryrun Bought 100 at 84000")["cmd"] == "bought"
    assert commands.parse("bought 100 of pepe at 1")["cmd"] == "unknown"


# ---- account maths ---------------------------------------------------------

def seed_account(state):
    return read(state, "account.json")


def test_sell_all_closes_the_position(state):
    fill = acct.sell(seed_account(state), "BTC", "all", 82150.0, "2026-10-03T12:00:00Z", "sold all at 82150")
    a = fill.account
    assert fill.closed and a["positions"] == []
    assert round(fill.realised_usd, 2) == -9.57  # 0.0049961 x 82,150 = 410.43 against 420
    assert a["balance_usd"] == 1040.43 and a["cash_usd"] == 1040.43
    assert a["closed_trades"][-1] == {"id": "trade-2", "asset": "BTC", "size_usd": 420.0,
                                      "opened_at": "2026-10-02T18:44:00Z", "closed_at": "2026-10-03T12:00:00Z",
                                      "result_usd": -9.57}
    assert a["last_confirmed_via"] == "telegram"


def test_sell_half_keeps_half_at_cost(state):
    fill = acct.sell(seed_account(state), "BTC", "half", 86800.0, "t", "x")
    pos = fill.account["positions"][0]
    assert pos["size_usd"] == 210.0 and pos["qty_btc"] == pytest.approx(0.00249805)
    assert round(fill.realised_usd, 2) == 6.83
    assert fill.account["balance_usd"] == 1056.83
    rest = acct.sell(fill.account, "BTC", "all", 88000.0, "t2", "y")
    assert rest.account["closed_trades"][-1]["size_usd"] == 420.0
    assert rest.account["closed_trades"][-1]["result_usd"] == round(6.83 + (0.00249805 * 88000 - 210), 2)


def test_buy_opens_a_position_and_moves_cash(state):
    closed = acct.sell(seed_account(state), "BTC", "all", 82150.0, "t", "x").account
    fill = acct.buy(closed, "BTC", 100.0, 84000.0, "2026-10-03T12:00:00Z", "bought 100 at 84000", price_eur=74550)
    pos = fill.account["positions"][0]
    assert pos["id"] == "trade-3" and pos["size_usd"] == 100.0 and pos["entry_usd"] == 84000.0
    assert fill.account["cash_usd"] == 940.43 and fill.account["balance_usd"] == 1040.43
    assert not fill.warnings


def test_buy_more_than_cash_warns(state):
    fill = acct.buy(seed_account(state), "BTC", 700.0, 84000.0, "t", "x")
    assert fill.warnings and "more than the cash" in fill.warnings[0]


# ---- Telegram ----------------------------------------------------------------

def test_dry_run_report_changes_nothing_but_shows_the_result(state):
    """SPEC.md milestone 2 acceptance: "Bought 100 at <price>" in dry-run mode."""
    before = (state / "account.json").read_text()
    notifier, _ = reply_to(state, msg(10, "/dryrun Bought 100 at 84000"))
    [(text, _)] = notifier.sent
    assert text.startswith("<b>DRY RUN, nothing changed.</b>")
    assert "Recorded: bought $100.00 of BTC at $84,000 (EUR 74,550)" in text
    assert "That is more than the cash" not in text
    assert "cash $530.00" in text
    assert (state / "account.json").read_text() == before
    assert inbox(state)[-1]["parsed"]["dry"] is True
    assert read(state, "telegram_offset.json") == {"offset": 11}


def test_sold_all_after_exit_fired_closes_trade_and_alerts(state):
    rearm(state)
    fire(state, "btc-exit")
    notifier = FakeNotifier(updates=[msg(5, "Sold all at 82150$")])
    run(state, notifier=notifier)
    text = notifier.sent[0][0]
    assert "Recorded: sold all your BTC at $82,150" in text and "result -$9.57" in text
    assert "Balance $1,040.43 (cost basis), cash $1,040.43." in text
    assert "Matched alert btc-exit: marked done." in text
    s = status(state)
    assert s["btc-exit"] == "done"
    assert s["btc-t1"] == s["btc-t2"] == s["btc-warning"] == "disabled"
    assert read(state, "account.json")["positions"] == []


def test_sold_half_after_t1_arms_breakeven(state):
    rearm(state)
    fire(state, "btc-t1")
    notifier = FakeNotifier(updates=[msg(5, "/sold half at 86817")])
    run(state, notifier=notifier)
    s = status(state)
    assert s["btc-t1"] == "done" and s["btc-breakeven"] == "armed"
    assert s["btc-exit"] == s["btc-warning"] == "disabled"
    assert s["btc-t2"] == "armed"
    be = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-breakeven")
    assert be["armed_at"] == "2026-10-03T12:00:40Z"
    assert "Now watching: btc-breakeven (below EUR 74,600 / $84,056)." in notifier.sent[0][0]


def test_done_button_applies_on_done_and_asks_for_the_price(state):
    rearm(state)
    fire(state, "btc-exit")
    notifier = FakeNotifier(updates=[press(6, "done:btc-exit")])
    run(state, notifier=notifier)
    assert notifier.answers == ["Recorded: done"] and notifier.removed == [77]
    assert "Send the price you got so the account is right: /sold all at &lt;price&gt;" in notifier.sent[0][0]
    exit_alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert exit_alert["status"] == "done" and exit_alert["awaiting_fill"] is True
    assert read(state, "account.json")["positions"]  # no fill inferred from a button

    notifier = FakeNotifier(updates=[msg(7, "sold all at 82150")])
    run(state, notifier=notifier, now=NOW + 60)
    exit_alert = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == "btc-exit")
    assert exit_alert["awaiting_fill"] is False
    assert read(state, "account.json")["positions"] == []


def test_not_done_button_skips(state):
    rearm(state)
    fire(state, "btc-t1")
    notifier = FakeNotifier(updates=[press(6, "skip:btc-t1")])
    run(state, notifier=notifier)
    assert status(state)["btc-t1"] == "skipped"
    assert status(state)["btc-breakeven"] == "disabled"
    assert "did not act on btc-t1" in notifier.sent[0][0]


def test_second_press_is_already_recorded(state):
    rearm(state)
    fire(state, "btc-exit")
    run(state, notifier=FakeNotifier(updates=[press(6, "done:btc-exit")]))
    notifier = FakeNotifier(updates=[press(7, "done:btc-exit")])
    run(state, notifier=notifier, now=NOW + 60)
    assert notifier.answers == ["Already recorded (done)."] and notifier.sent == []


def test_messages_from_anyone_else_are_ignored(state):
    before = (state / "inbox.jsonl").read_text()
    notifier, summary = reply_to(state, msg(8, "/sold all at 1", chat=999), press(9, "done:btc-exit", chat=999))
    assert notifier.sent == [] and notifier.answers == []
    assert (state / "inbox.jsonl").read_text() == before
    assert read(state, "telegram_offset.json") == {"offset": 10}


def test_unknown_text_is_saved_for_the_brief(state):
    notifier, _ = reply_to(state, msg(3, "Should I add on the dip?"))
    assert "saved it for the next brief" in notifier.sent[0][0]
    assert inbox(state)[-1]["text"] == "Should I add on the dip?"


def test_status_alerts_and_price_replies(state):
    notifier, _ = reply_to(state, msg(1, "/status"), msg(2, "/alerts"), msg(3, "/price"))
    status_text, alerts_text, price_text = (t for t, _ in notifier.sent)
    assert "Balance $1,050.00 (cost basis), cash $630.00." in status_text
    assert "BTC: 0.0049961 for $420.00, entry $84,065; now $84,000, worth $419.67 (-$0.33)." in status_text
    assert "Equity about $1,049.67: $70.33 to the $1,120 target, $99.67 above the $950 floor." in status_text
    assert alerts_text.startswith("<b>Watching 6 alerts</b> (BTC now EUR 74,550 / $84,000)")
    assert "- below EUR 72,800 / $82,028, 2.3% away: ACTION, SELL ALL" in alerts_text
    assert price_text.startswith("BTC now: EUR 74,550 / $84,000 (Kraken, EUR/USD 1.1268")


def test_offset_is_sent_back_on_the_next_run(state):
    notifier, _ = reply_to(state, msg(41, "/price"))
    notifier2 = FakeNotifier()
    run(state, notifier=notifier2)
    assert notifier2.offsets == [42]


def test_buy_without_an_exit_alert_warns(state):
    rearm(state)
    run(state, notifier=FakeNotifier(updates=[msg(1, "sold all at 82150")]))
    notifier = FakeNotifier(updates=[msg(2, "bought 100 at 84000")])
    run(state, notifier=notifier, now=NOW + 60)
    assert "No exit alert is set for this BTC position yet." in notifier.sent[0][0]


def test_sold_with_no_position_records_nothing(state):
    rearm(state)
    run(state, notifier=FakeNotifier(updates=[msg(1, "sold all at 82150")]))
    notifier = FakeNotifier(updates=[msg(2, "sold all at 82000")])
    run(state, notifier=notifier, now=NOW + 60)
    assert notifier.sent[0][0].startswith("Nothing recorded: no open BTC position on record.")


def test_action_alert_carries_buttons_and_watch_does_not(state):
    rearm(state)
    notifier = FakeNotifier()
    run(state, FakeKraken("ohlc_1m_wick.json"), notifier=notifier)
    assert notifier.markups[0] == {"inline_keyboard": [[
        {"text": "Done", "callback_data": "done:btc-exit"},
        {"text": "Not done", "callback_data": "skip:btc-exit"}]]}
    assert notifier.markups[1] is None
    assert "Tap Done once you've sold, or send /sold all at &lt;price&gt;." in notifier.sent[0][0]


def test_heartbeat_dry_run_does_not_store_reports(state):
    rearm(state)
    before = {p.name: p.read_text() for p in state.iterdir()}
    notifier = FakeNotifier(updates=[msg(1, "sold all at 82150")])
    run(state, notifier=notifier, write_state=False)
    assert notifier.sent
    assert {p.name: p.read_text() for p in state.iterdir()} == before
