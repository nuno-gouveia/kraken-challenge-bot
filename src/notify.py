"""Tell Nuno on Telegram which alerts are now set (notify-alerts.yml).

    python -m src.notify [--before OLD_ALERTS_JSON] [--dry-run]

Runs when a push (the daily brief, or a person) changes state/alerts.json.
The heartbeat's own commits never trigger it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

from src import alerts, kraken, quiet_hours, telegram
from src.messages import NFA, both, escape, lisbon, listing_order, num, trigger


def live(doc: dict) -> dict[str, dict]:
    return {a["id"]: a for a in doc.get("alerts", []) if isinstance(a, dict) and a.get("status") in alerts.LIVE}


def changes(before: dict | None, after: dict) -> list[str]:
    if before is None:
        return []
    old, new = live(before), live(after)
    out = []
    added = [i for i in new if i not in old]
    removed = [i for i in old if i not in new]
    moved = [i for i in new if i in old
             and (old[i].get("level"), old[i].get("at")) != (new[i].get("level"), new[i].get("at"))]
    if added:
        out.append("new " + ", ".join(escape(i) for i in added))
    if removed:
        out.append("removed " + ", ".join(escape(i) for i in removed))
    for i in moved:
        if alerts.is_timed(new[i]) and alerts.is_timed(old[i]):
            now = time.time()
            out.append(f"{escape(i)} moved from {trigger(old[i], None, now)} to {trigger(new[i], None, now)}")
            continue
        if alerts.is_timed(new[i]) or alerts.is_timed(old[i]):
            out.append(f"{escape(i)} changed")
            continue
        quote = new[i]["pair"][-3:]
        out.append(f"{escape(i)} moved from {quote} {num(old[i]['level'])} to {quote} {num(new[i]['level'])}")
    return out


def condition(a: dict, rate: float | None, eur: float | None, now: float) -> str:
    """When an alert would go off, in words: "BTC rises to EUR 78,200 / $87,483 (2.4% away)"."""
    if alerts.is_timed(a):
        return f"it is {lisbon(alerts.parse_ts(a['at']), now)} Lisbon"
    quote = a["pair"][-3:]
    level = both(a["level"], quote, rate) if rate else f"{quote} {num(a['level'])}"
    dist = f" ({abs(a['level'] / eur - 1) * 100:.1f}% away)" if eur and a["pair"] == "XBTEUR" else ""
    move = "falls to" if a["direction"] == "below" else "rises to"
    return f"{alerts.pair_asset(a['pair'])} {move} {level}{dist}"


def holdings(account: dict | None) -> str | None:
    if not account:
        return None
    held = []
    for pos in account.get("positions", []):
        name = pos.get("asset", "?")
        qty = pos.get("qty", pos.get(f"qty_{name.lower()}"))
        size = pos.get("size_usd")
        if isinstance(qty, (int, float)) and isinstance(size, (int, float)):
            held.append(f"{qty:g} {name}, bought for ${size:,.2f}")
    if held:
        return "You hold: " + "; ".join(held) + "."
    cash = account.get("cash_usd")
    return "You hold no position" + (f", all cash (${cash:,.2f})." if isinstance(cash, (int, float)) else ".")


def message(doc: dict, before: dict | None, last: dict[str, float] | None, now: float,
            account: dict | None = None) -> str:
    """A list of what could happen, never a list of orders: every alert is
    written as "if this, you'll be told that", and nothing in it is to do now."""
    rate = last["XBTUSD"] / last["XBTEUR"] if last else doc.get("eur_usd")
    eur = last["XBTEUR"] if last else None
    alerts_now = sorted(live(doc).values(), key=listing_order)
    lines = [f"<b>Alerts updated. Nothing to do now.</b> ({lisbon(now, now)} Lisbon, by "
             f"{escape(str(doc.get('updated_by', '?')))})"]
    held = holdings(account)
    if held:
        lines.append(escape(held))
    if eur:
        lines.append(f"BTC now EUR {num(eur)} / ${num(eur * rate)} (Kraken, EUR/USD {rate:.4f}).")
    if not alerts_now:
        lines.append("No alerts are set: nothing is being watched.")
    for kind, title in (("action", "You'll be told to act only if:"), ("watch", "Silent notes, nothing to do, if:")):
        group = [a for a in alerts_now if a.get("kind") == kind]
        if not group:
            continue
        lines.append("")
        lines.append(f"<b>{title}</b>")
        for a in group:
            lines.append(f"- {condition(a, rate, eur, now)}: \"{escape(a['message'])}\"")
    lines.append("")
    diff = changes(before, doc)
    if diff:
        lines.append("Changed: " + "; ".join(diff) + ".")
    lines.append("Action alerts due between 22:30 and 06:30 wait for the 06:30 re-check.")
    lines.append(NFA)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alerts", type=Path, default=Path("state/alerts.json"))
    parser.add_argument("--before", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    doc = alerts.load(args.alerts)
    before = None
    if args.before and args.before.exists() and args.before.stat().st_size:
        try:
            before = json.loads(args.before.read_text())
        except ValueError:
            before = None
    if before is not None and live(before) == live(doc):
        print("notify: live alerts unchanged, nothing to send")
        return 0

    session = requests.Session()
    try:
        last = kraken.ticker_last(session, ["XBTEUR", "XBTUSD"])
    except kraken.KrakenError as exc:
        print(f"notify: {exc}")
        last = None
    now = time.time()
    try:
        account = json.loads((args.alerts.parent / "account.json").read_text())
    except (OSError, ValueError):
        account = None
    text = message(doc, before, last, now, account)
    if args.dry_run:
        print(text)
        return 0
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        return 2
    try:
        telegram.send_message(session, token, chat_id, text, silent=quiet_hours.is_quiet(now))
    except telegram.TelegramError as exc:
        print(f"telegram: {exc}")
        return 1
    print(f"notify: sent ({len(live(doc))} live alerts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
