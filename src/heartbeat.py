"""Heartbeat: one run every 5 minutes from .github/workflows/heartbeat.yml.

Reads the alerts, fetches Kraken candles since each alert was armed, sends a
Telegram message for every alert hit and marks it fired, so it fires once.
Writes state/ only when something changed; the workflow commits it.

    python -m src.heartbeat [--dry-run] [--summary-file PATH]

--dry-run (or HEARTBEAT_DRY_RUN=1) prints the messages instead of sending
them and writes nothing, so a dry run never uses up a live alert.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path

import requests

from src import alerts, messages, prices as price_source, telegram

FAILURES_BEFORE_OUTAGE = 3
HEARTBEAT_DEFAULTS = {"price_failures": 0, "outage_notified": False, "alerts_problems": []}


class Notifier:
    def __init__(self, session: requests.Session, token: str | None, chat_id: str | None, dry_run: bool):
        self.session, self.token, self.chat_id, self.dry_run = session, token, chat_id, dry_run
        self.failed = False

    def send(self, text: str, silent: bool = False) -> bool:
        """True once Telegram has accepted the message."""
        if self.dry_run:
            print(f"--- dry run: would send{' (silent)' if silent else ''} ---\n{text}\n---")
            return True
        try:
            telegram.send_message(self.session, self.token, self.chat_id, text, silent=silent)
            return True
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")
            self.failed = True
            return False


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return copy.deepcopy(default)


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def run(state_dir: Path, notifier: Notifier, session: requests.Session, cmc_key: str | None,
        now_fn=time.time, sleep=time.sleep, write: bool = True) -> list[str]:
    """One heartbeat. Returns a summary of what changed, for the commit message."""
    now = now_fn()
    summary: list[str] = []
    hb_path, alerts_path = state_dir / "heartbeat.json", state_dir / "alerts.json"
    hb = {**HEARTBEAT_DEFAULTS, **read_json(hb_path, {})}
    hb_before = copy.deepcopy(hb)
    account = read_json(state_dir / "account.json", None)

    try:
        doc = alerts.load(alerts_path)
    except alerts.AlertsFileError as exc:
        doc, doc_before, bad = None, None, [str(exc)]
    else:
        doc_before = copy.deepcopy(doc)
        for a in doc["alerts"]:
            if isinstance(a, dict) and a.get("status") == "armed" and not a.get("armed_at"):
                a["armed_at"] = alerts.iso(now)
                print(f"alerts: {a.get('id')} had no armed_at, armed from now")
        bad = alerts.problems(doc, now)
    for p in bad:
        print(f"alerts: {p}")
    if bad != hb["alerts_problems"]:
        text = messages.problems_message(bad) if bad else messages.problems_cleared_message()
        if notifier.send(text):
            hb["alerts_problems"] = bad
            summary.append("alerts file problems" if bad else "alerts file fixed")

    live = alerts.watchable(doc, bad) if doc else []
    if live:
        since: dict[str, int] = {}
        for a in live:
            t = int(alerts.parse_ts(a["armed_at"]))
            since[a["pair"]] = min(since.get(a["pair"], t), t)
        try:
            p = price_source.fetch(session, since, cmc_key, now_fn=now_fn, sleep=sleep)
        except price_source.NoPrices as exc:
            print(f"prices: {exc}")
            p = None

        if p is None:
            hb["price_failures"] = min(hb["price_failures"] + 1, FAILURES_BEFORE_OUTAGE)
            if hb["price_failures"] >= FAILURES_BEFORE_OUTAGE and not hb["outage_notified"]:
                if notifier.send(messages.outage_message(FAILURES_BEFORE_OUTAGE)):
                    hb["outage_notified"] = True
                    summary.append("prices down")
        else:
            print(f"prices: {p.source}, " + ", ".join(f"{k} {v:,.2f}" for k, v in sorted(p.last.items())))
            if hb["outage_notified"] and notifier.send(messages.recovered_message(p)):
                hb["outage_notified"] = False
                summary.append("prices back")
            hb["price_failures"] = 0
            now = now_fn()
            for a in live:
                hit = alerts.evaluate(a, p.candles[a["pair"]], now)
                if hit is None:
                    continue
                if hit.authorised:
                    text = messages.alert_message(hit, p, account, now)
                    if notifier.send(text, silent=a["kind"] == "watch"):
                        a.update(status="fired", fired_at=alerts.iso(now), fired_source=p.source)
                        summary.append(f"fired {a['id']}")
                else:
                    if notifier.send(messages.gate_message(hit, p, now), silent=True):
                        a["gate_notified_at"] = alerts.iso(now)
                        summary.append(f"{a['id']} touched outside its window")
                print(f"alerts: {a['id']} hit ({'authorised' if hit.authorised else 'outside window'})")

    if write:
        if doc is not None and doc != doc_before:
            alerts.save(alerts_path, doc)
        if hb != hb_before:
            write_json(hb_path, hb)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", default=os.environ.get("HEARTBEAT_DRY_RUN") == "1")
    parser.add_argument("--state-dir", type=Path, default=Path("state"))
    parser.add_argument("--summary-file", type=Path)
    args = parser.parse_args(argv)

    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not args.dry_run and not (token and chat_id):
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set (or use --dry-run)")
        return 2

    session = requests.Session()
    notifier = Notifier(session, token, chat_id, args.dry_run)
    summary = run(args.state_dir, notifier, session, os.environ.get("CMC_API_KEY") or None,
                  write=not args.dry_run)
    if args.summary_file:
        args.summary_file.write_text("heartbeat: " + ("; ".join(summary) or "update state") + "\n")
    print("summary: " + ("; ".join(summary) or "nothing to report"))
    return 1 if notifier.failed else 0


if __name__ == "__main__":
    sys.exit(main())
