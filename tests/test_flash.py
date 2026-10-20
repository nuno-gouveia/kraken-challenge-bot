"""Flash dip: detection in the heartbeat, the buy message, exits from the real fill."""

from src import flash, validate_alerts
from src.kraken import Candle
from tests.conftest import NOW, T, FakeKraken, FakeNotifier, FakeResponse, read, write
from tests.test_heartbeat import run, status
from tests.test_inbound import msg, press

ON = {"enabled": True}


class FakeDip(FakeKraken):
    """Kraken with BTC/EUR at 78,500 three hours ago and 74,550 now (5.0% down)."""

    def __init__(self, top=78500.0, now=NOW):
        super().__init__()
        self.top, self.now = top, now

    def get(self, url, params=None, timeout=None, headers=None):
        if url.endswith("/OHLC"):
            self.calls.append((url, dict(params or {})))
            start = int(self.now) - 5 * 3600
            start -= start % 60
            rows, n = [], (int(self.now) - start) // 60
            for i in range(n + 1):
                t = start + i * 60
                px = self.top if t == start + 2 * 3600 else 74600.0 - i * 0.1
                rows.append([t, str(px), str(px), str(px - 5), str(px), str(px), "1", 1])
            return FakeResponse({"error": [], "result": {"XXBTZEUR": rows, "last": rows[-1][0]}})
        return super().get(url, params, timeout, headers)


def cash_only(state, cash=1054.56):
    acct = read(state, "account.json")
    acct.update(positions=[], cash_usd=cash, balance_usd=cash)
    write(state, "account.json", acct)
    doc = read(state, "alerts.json")
    for a in doc["alerts"]:
        a["status"] = "disabled"
    write(state, "alerts.json", doc)


def flash_alert(state):
    return next(a for a in read(state, "alerts.json")["alerts"] if a["id"].startswith("flash-") and "flash" in a)


def test_detect_needs_the_full_drop_inside_the_window():
    cfg = dict(flash.DEFAULTS)
    candles = [Candle(int(NOW) - 3 * 3600, 0, 78500, 78400, 78450), Candle(int(NOW) - 60, 0, 74700, 74500, 74550)]
    assert flash.detect(candles, 74550, NOW, cfg) == (78500, int(NOW) - 3 * 3600)
    assert flash.detect(candles, 74800, NOW, cfg) is None  # only 4.7% down
    old = [Candle(int(NOW) - 5 * 3600, 0, 78500, 78400, 78450)] + candles[1:]
    assert flash.detect(old, 74550, NOW, cfg) is None  # the high is outside the 4 hours


def test_size_risks_2pct_capped_at_40pct():
    assert flash.size_usd({"cash_usd": 1054.56}, flash.DEFAULTS) == 420
    assert flash.size_usd({"cash_usd": 2000}, flash.DEFAULTS) == 800  # 2% / 4% = 50%, cap 40%


def test_signal_goes_out_once_with_the_plan(state):
    cash_only(state)
    notifier, summary = run(state, FakeDip(), flash_cfg=ON)
    [(text, silent)] = notifier.sent
    assert silent is False and notifier.markups[0]["inline_keyboard"][0][0]["callback_data"].startswith("done:flash-")
    assert text.startswith("<b>ACTION: BUY $420 of BTC at market now (flash dip).</b>")
    assert "BTC fell 5.0% in the last hours: from EUR 78,500" in text
    assert "<b>Only buy if you can do it within 15 minutes.</b>" in text
    assert "- Sell at +2%: about EUR 76,000 / $85,634" in text
    assert "- Exit at -4%: about EUR 71,600 / $80,676" in text
    assert "- Or sell after 24 hours: 4 Oct 13:00 Lisbon" in text
    assert "/bought 420 at &lt;price&gt;" in text and text.endswith("Not financial advice.")
    a = flash_alert(state)
    assert a["status"] == "fired" and a["trade"] == "buy" and a["flash"]["size_usd"] == 420
    assert read(state, "heartbeat.json")["flash_signal_at"] == "2026-10-03T12:00:40Z"
    assert summary == [f"flash dip: {a['id']}"]

    notifier, summary = run(state, FakeDip(now=NOW + 300), now=NOW + 300, flash_cfg=ON)
    assert notifier.sent == [] and summary == []  # the buy is still waiting


def test_no_signal_in_quiet_hours_with_a_position_or_when_off(state):
    night = T("2026-10-03T22:00:40")  # 23:00 Lisbon
    cash_only(state)
    notifier, _ = run(state, FakeDip(now=night), now=night, flash_cfg=ON)
    assert notifier.sent == []
    notifier, _ = run(state, FakeDip(), flash_cfg={"enabled": False})
    assert notifier.sent == []
    acct = read(state, "account.json")
    acct["positions"] = [{"id": "x", "asset": "BTC", "side": "long", "size_usd": 100, "qty_btc": 0.001}]
    write(state, "account.json", acct)
    notifier, _ = run(state, FakeDip(), flash_cfg=ON)
    assert notifier.sent == []


def test_done_arms_exits_and_bought_moves_them_to_the_real_price(state):
    cash_only(state)
    run(state, FakeDip(), flash_cfg=ON)
    aid = flash_alert(state)["id"]

    notifier = FakeNotifier(updates=[press(6, f"done:{aid}")])
    run(state, FakeDip(now=NOW + 60), notifier=notifier, now=NOW + 60, flash_cfg=ON)
    reply = notifier.sent[0][0]
    assert "Exits set from the signal price for now" in reply
    assert "/bought 420 at &lt;price&gt;" in reply
    s = status(state)
    assert s[f"{aid}-target"] == s[f"{aid}-stop"] == s[f"{aid}-time"] == "armed"
    tgt = next(a for a in read(state, "alerts.json")["alerts"] if a["id"] == f"{aid}-target")
    assert tgt["level"] == 76000

    notifier = FakeNotifier(updates=[msg(7, "/bought 420 at 83000")])
    run(state, FakeDip(now=NOW + 120), notifier=notifier, now=NOW + 120, flash_cfg=ON)
    reply = notifier.sent[0][0]
    assert "<b>Flash-dip exits set from your price.</b>" in reply
    doc = read(state, "alerts.json")
    by = {a["id"]: a for a in doc["alerts"]}
    entry_eur = 83000 / (84000 / 74550)
    assert by[f"{aid}-target"]["level"] == (entry_eur * 1.02) // 50 * 50
    assert by[f"{aid}-stop"]["level"] == -(-entry_eur * 0.96 // 50) * 50
    assert by[f"{aid}-time"]["at"] == "2026-10-04T12:01:40Z"  # 24h from the Done tap, unchanged
    assert by[aid]["awaiting_fill"] is False
    assert read(state, "account.json")["positions"][0]["size_usd"] == 420
    errors, _ = validate_alerts.check(doc, NOW + 120)
    assert errors == []

    # One position at a time: no new signal while it is open.
    notifier, _ = run(state, FakeDip(now=NOW + 5 * 3600), now=NOW + 5 * 3600, flash_cfg=ON)
    assert not any("BUY" in t for t, _ in notifier.sent)


def test_bought_without_done_still_sets_the_exits(state):
    cash_only(state)
    run(state, FakeDip(), flash_cfg=ON)
    aid = flash_alert(state)["id"]
    notifier = FakeNotifier(updates=[msg(7, "Bought 420$ at 83500$")])
    run(state, FakeDip(now=NOW + 120), notifier=notifier, now=NOW + 120, flash_cfg=ON)
    s = status(state)
    assert s[aid] == "done" and s[f"{aid}-target"] == s[f"{aid}-stop"] == s[f"{aid}-time"] == "armed"


def test_an_exit_disarms_the_other_two(state):
    from src import alerts
    cash_only(state)
    run(state, FakeDip(), flash_cfg=ON)
    doc = read(state, "alerts.json")
    buy = next(a for a in doc["alerts"] if a["id"].startswith("flash-") and "flash" in a)
    flash.arm_exits(doc, buy, 74550, NOW, 1.1268)
    target = alerts.by_id(doc, f"{buy['id']}-target")
    alerts.mark_done(doc, target, "2026-10-03T13:00:00Z", "button")
    assert alerts.by_id(doc, f"{buy['id']}-stop")["status"] == "disabled"
    assert alerts.by_id(doc, f"{buy['id']}-time")["status"] == "disabled"


def test_unanswered_buy_lapses_after_two_hours_and_unblocks(state):
    cash_only(state)
    run(state, FakeDip(), flash_cfg=ON)
    later = NOW + 5 * 3600
    notifier, summary = run(state, FakeDip(now=later), now=later, flash_cfg=ON)
    assert f"{flash_alert(state)['id']} lapsed" in summary[0]
    assert any("BUY $420" in t for t, _ in notifier.sent)  # a fresh dip in a new window signals again


def test_not_done_lets_it_go(state):
    cash_only(state)
    run(state, FakeDip(), flash_cfg=ON)
    aid = flash_alert(state)["id"]
    run(state, FakeDip(now=NOW + 60), notifier=FakeNotifier(updates=[press(6, f"skip:{aid}")]), now=NOW + 60, flash_cfg=ON)
    assert status(state)[aid] == "skipped"
    assert not any(a.startswith(f"{aid}-") for a in status(state))
