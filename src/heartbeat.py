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

from src import alerts, gaps, inbound, messages, prices as price_source, quiet_hours, telegram

FAILURES_BEFORE_OUTAGE = 3
HEARTBEAT_DEFAULTS = {"price_failures": 0, "outage_notified": False, "alerts_problems": []}


class Notifier:
    """The bot, as the heartbeat uses it. In dry-run mode it reads updates
    but only prints what it would send."""

    def __init__(self, session: requests.Session, token: str | None, chat_id: str | None, dry_run: bool):
        self.session, self.token, self.chat_id, self.dry_run = session, token, chat_id, dry_run
        self.failed = False

    def send(self, text: str, silent: bool = False, reply_markup: dict | None = None) -> bool:
        """True once Telegram has accepted the message."""
        if self.dry_run:
            extra = (" (silent)" if silent else "") + (" (with Done / Not done)" if reply_markup else "")
            print(f"--- dry run: would send{extra} ---\n{text}\n---")
            return True
        try:
            telegram.send_message(self.session, self.token, self.chat_id, text, silent=silent, reply_markup=reply_markup)
            return True
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")
            self.failed = True
            return False

    def updates(self, offset: int | None) -> list[dict]:
        if not self.token:
            return []
        try:
            return telegram.get_updates(self.session, self.token, offset)
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")
            self.failed = True
            return []

    def answer(self, callback_id: str, text: str) -> None:
        if self.dry_run:
            print(f"--- dry run: would answer a button press: {text} ---")
            return
        try:
            telegram.answer_callback(self.session, self.token, callback_id, text)
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")

    def remove_buttons(self, chat_id, message_id) -> None:
        if self.dry_run or chat_id is None or message_id is None:
            return
        try:
            telegram.remove_buttons(self.session, self.token, chat_id, message_id)
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return copy.deepcopy(default)


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def morning_recheck(live: list[dict], held: list[dict], p, now: float) -> dict[str, tuple[dict, float]]:
    """First run after quiet hours: every action due overnight is armed again
    from 06:30, so it fires now only if the price is still through its level.

    Covers alerts the night runs held, and action alerts first touched during
    the night that no run saw (e.g. GitHub skipped the night's runs).
    Returns id -> (alert, first touch time).
    """
    q_start, q_end = quiet_hours.last_window(now)
    overnight = {}
    for a in held:
        overnight[a["id"]] = (a, alerts.parse_ts(a.get("held_first_touch_at")) or q_end)
    for a in live:
        if a["kind"] != "action":
            continue
        hit = alerts.evaluate(a, p.candles[a["pair"]], now)
        if hit and hit.authorised and q_start <= hit.first_touch.time < q_end:
            overnight[a["id"]] = (a, hit.first_touch.time)
    for a, first in overnight.values():
        a.pop("held_at", None)
        a.pop("held_first_touch_at", None)
        a.update(status="armed", armed_at=alerts.iso(q_end),
                 held_overnight={"first_touch_at": alerts.iso(first), "rechecked_at": alerts.iso(q_end)})
    return overnight


def overnight_entries(overnight, hits, p, now):
    q_end = quiet_hours.last_window(now)[1]
    fired = {h.alert["id"] for h in hits if h.authorised}
    entries = []
    for aid, (a, first) in overnight.items():
        night = [c for c in p.candles[a["pair"]] if first <= c.time < q_end]
        if a["direction"] == "below":
            extreme = min((c.low for c in night), default=a["level"])
        else:
            extreme = max((c.high for c in night), default=a["level"])
        entries.append((a, first, extreme, aid in fired))
    return entries


def run(state_dir: Path, notifier: Notifier, session: requests.Session, cmc_key: str | None,
        now_fn=time.time, sleep=time.sleep, write: bool = True, last_ok: float | None = None) -> list[str]:
    """One heartbeat. Returns a summary of what changed, for the commit message.

    last_ok: when the previous successful run finished (from GitHub). After a
    gap of more than gaps.GAP_AFTER_S, Nuno is told once the window is checked.
    """
    now = now_fn()
    started = now
    gap_from = last_ok if last_ok is not None and now - last_ok > gaps.GAP_AFTER_S else None
    quiet = quiet_hours.is_quiet(now)
    summary: list[str] = []
    hb_path, alerts_path = state_dir / "heartbeat.json", state_dir / "alerts.json"
    hb = {**HEARTBEAT_DEFAULTS, **read_json(hb_path, {})}
    hb_before = copy.deepcopy(hb)
    account_path = state_dir / "account.json"
    account = read_json(account_path, None)
    account_before = copy.deepcopy(account)

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
        bad = []
    # Nuno's reports first, so a fill he sent is in the account (and its
    # alerts armed or disarmed) before any alert is checked.
    rx = inbound.Inbound(state_dir, notifier, getattr(notifier, "chat_id", None), session, now,
                         dry_run=not write)
    doc, account = rx.run(doc, account)
    summary += rx.summary
    if doc is not None:
        bad = alerts.problems(doc, now)

    for p in bad:
        print(f"alerts: {p}")
    if bad != hb["alerts_problems"]:
        text = messages.problems_message(bad) if bad else messages.problems_cleared_message()
        if notifier.send(text, silent=quiet):
            hb["alerts_problems"] = bad
            summary.append("alerts file problems" if bad else "alerts file fixed")

    live = alerts.watchable(doc, bad) if doc else []
    # Time alerts fire on the clock. An action due in quiet hours waits for 06:30.
    timed = [a for a in live if alerts.is_timed(a)]
    live = [a for a in live if not alerts.is_timed(a)]
    due = [a for a in timed if alerts.due(a, now) and not (quiet and a["kind"] == "action")]
    held = [a for a in doc["alerts"] if isinstance(a, dict) and a.get("status") == "held"] if doc else []
    p = None
    hits: list = []
    if live or (held and not quiet) or due:
        since: dict[str, int] = {}
        for a in live + held:
            t = int(alerts.parse_ts(a["armed_at"]))
            since[a["pair"]] = min(since.get(a["pair"], t), t)
        for a in due:
            # Only the current price, for the message.
            since.setdefault(a["pair"], int(now) - 300)
        try:
            p = price_source.fetch(session, since, cmc_key, now_fn=now_fn, sleep=sleep)
        except price_source.NoPrices as exc:
            print(f"prices: {exc}")
            p = None

        if p is None:
            hb["price_failures"] = min(hb["price_failures"] + 1, FAILURES_BEFORE_OUTAGE)
            if hb["price_failures"] >= FAILURES_BEFORE_OUTAGE and not hb["outage_notified"]:
                if notifier.send(messages.outage_message(FAILURES_BEFORE_OUTAGE), silent=quiet):
                    hb["outage_notified"] = True
                    summary.append("prices down")
        else:
            print(f"prices: {p.source}, " + ", ".join(f"{k} {v:,.2f}" for k, v in sorted(p.last.items())))
            if hb["outage_notified"] and notifier.send(messages.recovered_message(p), silent=quiet):
                hb["outage_notified"] = False
                summary.append("prices back")
            hb["price_failures"] = 0
            now = now_fn()
            quiet = quiet_hours.is_quiet(now)
            overnight = morning_recheck(live, held, p, now) if not quiet else {}
            if overnight:
                live = live + [a for a in held if a not in live]
            hits = [h for h in (alerts.evaluate(a, p.candles[a["pair"]], now) for a in live) if h]
            if overnight:
                text = messages.morning_message(overnight_entries(overnight, hits, p, now), p, now)
                if notifier.send(text):
                    summary.append("morning update")
            for hit in hits:
                a = hit.alert
                print(f"alerts: {a['id']} hit ({'authorised' if hit.authorised else 'outside window'})")
                if hit.authorised and a["kind"] == "action" and quiet:
                    # Quiet hours: don't send, assume he doesn't act, re-check at 06:30.
                    a.update(status="held", held_at=alerts.iso(now),
                             held_first_touch_at=alerts.iso(hit.first_touch.time))
                    summary.append(f"held {a['id']} (quiet hours)")
                elif hit.authorised:
                    first = overnight.get(a["id"], (None, None))[1]
                    text = messages.alert_message(hit, p, account, now, overnight_at=first)
                    keyboard = messages.buttons(a["id"]) if a["kind"] == "action" else None
                    if notifier.send(text, silent=a["kind"] == "watch", reply_markup=keyboard):
                        a.update(status="fired", fired_at=alerts.iso(now), fired_source=p.source)
                        summary.append(f"fired {a['id']}")
                else:
                    if notifier.send(messages.gate_message(hit, p, now), silent=True):
                        a["gate_notified_at"] = alerts.iso(now)
                        summary.append(f"{a['id']} touched outside its window")

    for a in due:
        keyboard = messages.buttons(a["id"]) if a["kind"] == "action" else None
        text = messages.time_message(a, p, account, now)
        if notifier.send(text, silent=a["kind"] == "watch", reply_markup=keyboard):
            a.update(status="fired", fired_at=alerts.iso(now), fired_source=p.source if p else "clock")
            summary.append(f"fired {a['id']}")

    # Never report a gap that starts before the end of the last one reported,
    # whatever GitHub says (its run list has lagged by hours).
    reported_to = alerts.parse_ts(hb.get("gap_reported_to"))
    if gap_from is not None and reported_to is not None and gap_from < reported_to:
        print("gaps: already reported, skipping")
        gap_from = None
    if gap_from is not None:
        watched = bool(live or held)
        text = messages.gap_message(gap_from, started, now_fn(), watched=watched,
                                    checked=p is not None, touched=[h.alert["id"] for h in hits])
        if notifier.send(text, silent=quiet):
            hb["gap_reported_to"] = alerts.iso(started)
            summary.append("gap notice")

    if write:
        if doc is not None and doc != doc_before:
            alerts.save(alerts_path, doc)
        if hb != hb_before:
            write_json(hb_path, hb)
        if account is not None and account != account_before:
            write_json(account_path, account)
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
    gh_token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    last_ok = gaps.last_success_end(session, repo, gh_token, os.environ.get("GITHUB_RUN_ID")) \
        if gh_token and repo else None
    summary = run(args.state_dir, notifier, session, os.environ.get("CMC_API_KEY") or None,
                  write=not args.dry_run, last_ok=last_ok)
    if args.summary_file:
        args.summary_file.write_text("heartbeat: " + ("; ".join(summary) or "update state") + "\n")
    print("summary: " + ("; ".join(summary) or "nothing to report"))
    return 1 if notifier.failed else 0


if __name__ == "__main__":
    sys.exit(main())
