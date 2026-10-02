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
from src.messages import NFA, both, escape, lisbon, num


def live(doc: dict) -> dict[str, dict]:
    return {a["id"]: a for a in doc.get("alerts", []) if isinstance(a, dict) and a.get("status") in alerts.LIVE}


def changes(before: dict | None, after: dict) -> list[str]:
    if before is None:
        return []
    old, new = live(before), live(after)
    out = []
    added = [i for i in new if i not in old]
    removed = [i for i in old if i not in new]
    moved = [i for i in new if i in old and old[i].get("level") != new[i].get("level")]
    if added:
        out.append("new " + ", ".join(escape(i) for i in added))
    if removed:
        out.append("removed " + ", ".join(escape(i) for i in removed))
    for i in moved:
        quote = new[i]["pair"][-3:]
        out.append(f"{escape(i)} moved from {quote} {num(old[i]['level'])} to {quote} {num(new[i]['level'])}")
    return out


def message(doc: dict, before: dict | None, last: dict[str, float] | None, now: float) -> str:
    rate = last["XBTUSD"] / last["XBTEUR"] if last else doc.get("eur_usd")
    eur = last["XBTEUR"] if last else None
    alerts_now = sorted(live(doc).values(), key=lambda a: -a["level"])
    lines = [f"<b>Today's alerts are set</b> ({lisbon(now, now)} Lisbon, by {escape(str(doc.get('updated_by', '?')))})"]
    if eur:
        lines.append(f"BTC now EUR {num(eur)} / ${num(eur * rate)} (Kraken, EUR/USD {rate:.4f}).")
    if not alerts_now:
        lines.append("No alerts are set: nothing is being watched.")
    for kind, title in (("action", "Action (you'll be asked to act)"), ("watch", "Watch only (silent)")):
        group = [a for a in alerts_now if a.get("kind") == kind]
        if not group:
            continue
        lines.append(f"<b>{title}</b>")
        for a in group:
            quote = a["pair"][-3:]
            level = both(a["level"], quote, rate) if rate else f"{quote} {num(a['level'])}"
            dist = f", {abs(a['level'] / eur - 1) * 100:.1f}% away" if eur and a["pair"] == "XBTEUR" else ""
            lines.append(f"- {a['direction']} {level}{dist}: {escape(a['message'])}")
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
    text = message(doc, before, last, now)
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
