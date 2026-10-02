"""Telegram inbound (SPEC.md milestone 2): Nuno's reports, commands and button presses.

Runs at the start of every heartbeat. Only messages from TELEGRAM_CHAT_ID
are read; anything else is skipped without logging its content. Every
message from Nuno goes into state/inbox.jsonl verbatim.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from src import account as acct
from src import alerts, commands, kraken
from src.messages import NFA, both, escape, lisbon, money, num, signed_usd

PASS_USD, FAIL_USD = 1120.0, 950.0

# Kraken pairs per asset, for live prices in replies.
USD_PAIRS = {"BTC": "XBTUSD", "ETH": "ETHUSD", "LINK": "LINKUSD", "BCH": "BCHUSD", "DOGE": "XDGUSD", "SHIB": "SHIBUSD"}

HELP = "\n".join([
    "<b>What I understand</b>",
    "/bought 420 at 84065 (USD amount, USD price; add an asset like eth, default BTC)",
    "/sold all at 82150, /sold half at 86800, /sold 200 at 86800",
    "Prices in EUR work too: /sold all at 72900 eur",
    "/status: balance, cash, position, distance to target and floor",
    "/alerts: what I'm watching",
    "/price: BTC now",
    "/dryrun followed by any of these: shows the result, changes nothing",
    "Plain text works too: \"Bought 420$ at 84065$\".",
])


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LivePrices:
    """Kraken prices fetched on first use and cached for the run. None when Kraken can't be read."""

    def __init__(self, session):
        self.session = session
        self._last: dict[str, float] = {}
        self._failed: set[str] = set()

    def _get(self, pairs: list[str]) -> dict[str, float] | None:
        key = ",".join(pairs)
        if key in self._failed:
            return None
        if not all(p in self._last for p in pairs):
            try:
                self._last.update(kraken.ticker_last(self.session, pairs))
            except kraken.KrakenError as exc:
                print(f"inbound prices: {exc}")
                self._failed.add(key)
                return None
        return self._last

    @property
    def eur_usd(self) -> float | None:
        last = self._get(["XBTEUR", "XBTUSD"])
        return last["XBTUSD"] / last["XBTEUR"] if last else None

    def usd(self, asset: str) -> float | None:
        pair = USD_PAIRS.get(asset)
        last = self._get([pair]) if pair else None
        return last[pair] if last else None

    def btc_eur(self) -> float | None:
        last = self._get(["XBTEUR", "XBTUSD"])
        return last["XBTEUR"] if last else None


class Inbound:
    def __init__(self, state_dir: Path, bot, chat_id: str | None, session, now: float, dry_run: bool = False):
        self.state_dir, self.bot, self.chat_id, self.now, self.dry_run = state_dir, bot, str(chat_id or ""), now, dry_run
        self.prices = LivePrices(session)
        self.summary: list[str] = []
        self.inbox: list[dict] = []
        self._dry = False  # the message being handled is a /dryrun

    # ---- state -----------------------------------------------------------

    def run(self, doc: dict | None, account: dict | None) -> tuple[dict | None, dict | None]:
        """Process pending updates. Returns the (possibly changed) alerts doc and account."""
        offset_path = self.state_dir / "telegram_offset.json"
        try:
            offset = json.loads(offset_path.read_text()).get("offset")
        except (OSError, ValueError):
            offset = None
        updates = self.bot.updates(offset)
        if not updates:
            return doc, account
        for upd in sorted(updates, key=lambda u: u.get("update_id", 0)):
            try:
                doc, account = self.handle(upd, doc, account)
            except Exception as exc:  # one bad update must not stop alerts being checked
                print(f"inbound: update {upd.get('update_id')} failed: {type(exc).__name__}")
        last = max(u.get("update_id", 0) for u in updates)
        if not self.dry_run:
            offset_path.write_text(json.dumps({"offset": last + 1}) + "\n")
            if self.inbox:
                with (self.state_dir / "inbox.jsonl").open("a") as f:
                    for entry in self.inbox:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return doc, account

    def from_nuno(self, chat: dict | None) -> bool:
        return bool(self.chat_id) and str((chat or {}).get("id")) == self.chat_id

    def log(self, ts: float, text: str, parsed: dict, update_id: int) -> None:
        self.inbox.append({"ts": iso(ts), "text": text, "parsed": parsed, "update_id": update_id})

    def reply(self, text: str) -> None:
        self.bot.send(("<b>DRY RUN, nothing changed.</b>\n" if self._dry else "") + text)

    # ---- dispatch --------------------------------------------------------

    def handle(self, upd: dict, doc, account):
        if "callback_query" in upd:
            cq = upd["callback_query"]
            msg = cq.get("message") or {}
            if not self.from_nuno(msg.get("chat")):
                return doc, account
            return self.button(upd["update_id"], cq, doc, account)
        msg = upd.get("message") or {}
        if not self.from_nuno(msg.get("chat")):
            return doc, account
        text = msg.get("text") or ""
        parsed = commands.parse(text)
        self.log(msg.get("date", self.now), text, parsed, upd["update_id"])
        self._dry = parsed.get("dry", False)
        cmd = parsed["cmd"]
        if cmd == "help":
            self.reply(HELP)
        elif cmd == "status":
            self.reply(self.status_text(account, doc))
        elif cmd == "alerts":
            self.reply(self.alerts_text(doc))
        elif cmd == "price":
            self.reply(self.price_text())
        elif cmd in ("bought", "sold"):
            new_doc, new_account = self.report(parsed, text, doc, account)
            if not self._dry:
                doc, account = new_doc, new_account
        else:
            why = " (I don't trade that asset)" if parsed.get("why") == "unknown asset" else ""
            self.reply(f"I didn't understand that{why}, I've saved it for the next brief.\nSend /help for what I understand.")
            self.summary.append("saved a message for the brief")
        self._dry = False
        return doc, account

    # ---- reports ---------------------------------------------------------

    def to_usd(self, parsed: dict) -> tuple[float | None, float | None]:
        """(price in USD, price in EUR) from what he typed."""
        rate = self.prices.eur_usd
        if parsed["price_ccy"] == "EUR":
            return (parsed["price"] * rate if rate else None), parsed["price"]
        return parsed["price"], (parsed["price"] / rate if rate else None)

    def report(self, parsed: dict, text: str, doc, account):
        if account is None:
            self.reply("I can't read the account file, so I can't record that. Saved for the next brief.")
            return doc, account
        doc = copy.deepcopy(doc) if doc else None
        asset = parsed["asset"]
        price_usd, price_eur = self.to_usd(parsed)
        if price_usd is None:
            self.reply("I can't read Kraken's EUR/USD rate right now. Send the price in USD, e.g. /sold all at 82150.")
            return doc, account
        now_iso = iso(self.now)
        try:
            if parsed["cmd"] == "bought":
                fill = acct.buy(account, asset, parsed["usd"], price_usd, now_iso, text, price_eur)
            else:
                fill = acct.sell(account, asset, parsed["amount"], price_usd, now_iso, text)
        except ValueError as exc:
            self.reply(f"Nothing recorded: {escape(str(exc))}. If that's wrong, tell Claude in the brief chat.")
            return doc, account

        armed, disarmed, matched = [], [], None
        if doc is not None:
            if fill.side == "buy":
                trades = ("buy",)
            elif fill.closed:
                trades = ("sell_all", "sell_half")
            elif parsed.get("amount") == "half":
                trades = ("sell_half",)
            else:
                trades = ("sell_half", "sell_all")
            # None when he already tapped Done (or no alert asked for this): the
            # fill then only updates the account.
            matched = alerts.fired_for(doc, asset, trades)
            if matched is not None:
                armed, disarmed = alerts.mark_done(doc, matched, now_iso, "telegram report")
            for a in doc["alerts"]:
                if isinstance(a, dict) and a.get("awaiting_fill") and alerts.pair_asset(a.get("pair", "")) == asset:
                    a["awaiting_fill"] = False
            if fill.side == "sell" and fill.closed:
                disarmed += alerts.disarm_sells(doc, asset, f"{asset} position closed")

        lines = [self.fill_line(fill, price_eur)]
        lines += fill.warnings
        lines += self.account_lines(fill.account)
        if matched is not None:
            lines.append(f"Matched alert {escape(matched['id'])}: marked done.")
        if armed:
            lines.append("Now watching: " + ", ".join(self.alert_brief(alerts.by_id(doc, a)) for a in armed) + ".")
        if disarmed:
            lines.append("No longer watching: " + ", ".join(escape(a) for a in disarmed) + ".")
        if fill.side == "buy" and doc is not None and not alerts.sells_armed(doc, asset):
            lines.append(f"<b>No exit alert is set for this {asset} position yet.</b> Claude's next brief sets one; "
                         "until then nothing here watches it, so keep a Kraken app alert.")
        lines.append(NFA)
        self.reply("\n".join(lines))
        if not self._dry:
            self.summary.append(f"{'bought' if fill.side == 'buy' else 'sold'} {asset}")
        return doc, fill.account

    def fill_line(self, fill: acct.Fill, price_eur: float | None) -> str:
        eur = f" (EUR {num(price_eur)})" if price_eur else ""
        if fill.side == "buy":
            return f"<b>Recorded: bought ${fill.usd:,.2f} of {fill.asset} at ${num(fill.price_usd)}{eur}</b>, {fill.qty:.8g} {fill.asset}."
        what = "all your" if fill.closed else f"{fill.qty:.8g}"
        return (f"<b>Recorded: sold {what} {fill.asset} at ${num(fill.price_usd)}{eur}</b> for ${fill.usd:,.2f}, "
                f"result {signed_usd(fill.realised_usd)}.")

    def account_lines(self, account: dict) -> list[str]:
        balance, cash = float(account.get("balance_usd", 0)), float(account.get("cash_usd", 0))
        lines = [f"Balance ${balance:,.2f} (cost basis), cash ${cash:,.2f}."]
        equity = cash
        for pos in account.get("positions", []):
            qty = acct.qty_of(pos)
            px = self.prices.usd(pos["asset"])
            line = f"{pos['asset']}: {qty:.8g} for ${float(pos['size_usd']):,.2f}, entry ${num(float(pos['entry_usd']))}"
            if px:
                value = qty * px
                equity += value
                line += f"; now ${num(px)}, worth ${value:,.2f} ({signed_usd(value - float(pos['size_usd']))})"
            else:
                equity += float(pos["size_usd"])
            lines.append(line + ".")
        lines.append(f"Equity about ${equity:,.2f}: ${PASS_USD - equity:,.2f} to the ${PASS_USD:,.0f} target, "
                     f"${equity - FAIL_USD:,.2f} above the ${FAIL_USD:,.0f} floor.")
        if balance >= PASS_USD:
            lines.append("<b>Balance is at or above $1,120: the challenge target is reached.</b>")
        elif balance <= FAIL_USD:
            lines.append("<b>Balance is at or below $950: the challenge floor is touched.</b>")
        return lines

    # ---- buttons ---------------------------------------------------------

    def button(self, update_id: int, cq: dict, doc, account):
        data = cq.get("data") or ""
        action, _, aid = data.partition(":")
        msg = cq.get("message") or {}
        label = {"done": "Done", "skip": "Not done"}.get(action, action)
        self.log(cq.get("date", msg.get("date", self.now)), f"[button] {label} on {aid}",
                 {"cmd": "button", "action": action, "alert": aid}, update_id)
        alert = alerts.by_id(doc, aid) if doc else None
        if alert is None or alert.get("status") != "fired":
            state = alert.get("status") if alert else "gone"
            self.bot.answer(cq["id"], f"Already recorded ({state}).")
            self.bot.remove_buttons(msg.get("chat", {}).get("id"), msg.get("message_id"))
            return doc, account
        now_iso = iso(self.now)
        if action == "done":
            armed, disarmed = alerts.mark_done(doc, alert, now_iso, "button")
            trade = alerts.trade_of(alert)
            ask = {
                "buy": "/bought <usd> at <price>",
                "sell_half": "/sold half at <price>",
                "sell_all": "/sold all at <price>",
            }.get(trade)
            alert["awaiting_fill"] = ask is not None
            lines = [f"<b>Noted: {escape(aid)} done.</b>"]
            if ask:
                lines.append(f"Send the price you got so the account is right: {escape(ask)}")
            if armed:
                lines.append("Now watching: " + ", ".join(self.alert_brief(alerts.by_id(doc, a)) for a in armed) + ".")
            if disarmed:
                lines.append("No longer watching: " + ", ".join(escape(a) for a in disarmed) + ".")
            self.bot.answer(cq["id"], "Recorded: done")
            self.summary.append(f"{aid} done")
        else:
            alert.update(status="skipped", skipped_at=now_iso)
            lines = [f"<b>Noted: you did not act on {escape(aid)}.</b> Nothing changed in the account; "
                     "the next brief takes it from here."]
            self.bot.answer(cq["id"], "Recorded: not done")
            self.summary.append(f"{aid} skipped")
        self.bot.remove_buttons(msg.get("chat", {}).get("id"), msg.get("message_id"))
        self.bot.send("\n".join(lines))
        return doc, account

    # ---- read-only replies -----------------------------------------------

    def alert_brief(self, a: dict | None) -> str:
        if a is None:
            return "?"
        rate = self.prices.eur_usd
        level = both(a["level"], a["pair"][-3:], rate) if rate else money(a["level"], a["pair"][-3:])
        return f"{escape(a['id'])} ({a['direction']} {level})"

    def status_text(self, account: dict | None, doc: dict | None) -> str:
        if account is None:
            return "I can't read the account file right now."
        lines = [f"<b>Status</b> ({lisbon(self.now, self.now)} Lisbon)"]
        lines += self.account_lines(account)
        if doc:
            live = [a for a in doc["alerts"] if isinstance(a, dict) and a.get("status") in alerts.LIVE]
            lines.append(f"Alerts watching: {len(live)} (/alerts).")
        lines.append(f"Last report: {escape(str(account.get('last_confirmed_text', '?')))} "
                     f"({escape(str(account.get('last_confirmed_via', '?')))}).")
        lines.append(NFA)
        return "\n".join(lines)

    def price_text(self) -> str:
        eur, rate = self.prices.btc_eur(), self.prices.eur_usd
        if not eur:
            return "I can't read Kraken right now."
        return (f"BTC now: EUR {num(eur)} / ${num(eur * rate)} "
                f"(Kraken, EUR/USD {rate:.4f} from XBTUSD/XBTEUR, {lisbon(self.now, self.now)} Lisbon).")

    def alerts_text(self, doc: dict | None) -> str:
        if not doc:
            return "I can't read the alerts file right now."
        live = [a for a in doc["alerts"] if isinstance(a, dict) and a.get("status") in alerts.LIVE]
        if not live:
            return "No alerts are being watched."
        eur, rate = self.prices.btc_eur(), self.prices.eur_usd
        head = f"<b>Watching {len(live)} alerts</b>"
        if eur:
            head += f" (BTC now EUR {num(eur)} / ${num(eur * rate)})"
        lines = [head]
        for a in sorted(live, key=lambda a: -a["level"]):
            quote = a["pair"][-3:]
            level = both(a["level"], quote, rate) if rate else money(a["level"], quote)
            dist = ""
            if eur and a["pair"] == "XBTEUR":
                dist = f", {abs(a['level'] / eur - 1) * 100:.1f}% away"
            kind = "ACTION" if a["kind"] == "action" else "watch"
            held = " (held overnight)" if a["status"] == "held" else ""
            lines.append(f"- {a['direction']} {level}{dist}: {kind}{held}, {escape(a['message'])}")
        lines.append(NFA)
        return "\n".join(lines)
