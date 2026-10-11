"""Send Nuno a TLDR of each brief or event check on Telegram (notify-brief.yml).

    python -m src.tldr --before SHA --after SHA [--dry-run]

Runs when a push adds or changes analyses/*.md. For each such file it sends a
few lines taken straight from the file (docs/brief-format.md): the action,
the verdict, the position, today's steps and the alerts. The email keeps the
detail. A file changed rather than added (a brief fixed after a late Telegram
report) is sent again, marked "updated".
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time

import requests

from src import quiet_hours, telegram
from src.brief_email import NUMBERED, PRICE_ALERT, TIME_ALERT, inline, parse

NFA = "Not financial advice."
MAX_STEPS = 3


def title(subject: str) -> str:
    """'[NEW SYSTEM, compare only] BTC brief 6 Oct - HOLD: ...' -> 'Brief 6 Oct - HOLD: ...'."""
    s = re.sub(r"^\[[^\]]*\]\s*", "", subject)
    s = re.sub(r"^BTC\s+", "", s)
    return s[:1].upper() + s[1:]


def message(md: str, updated: bool = False) -> str:
    doc = parse(md)
    sections = {s["name"]: s["lines"] for s in doc["sections"]}
    lines = [f"<b>TLDR: {inline(title(doc['subject']))}</b>" + (" (updated)" if updated else "")]
    if doc["action"]:
        lines.append(f"<b>{inline(doc['action'])}</b>")
    if doc["verdict"]:
        lines.append(inline(doc["verdict"]))

    for line in sections.get("ACCOUNT", []):
        if line.startswith(("Position:", "BTC now:")):
            lines.append(inline(line))

    steps = [NUMBERED.match(x).group(2) for x in sections.get("WHAT TO DO", []) if NUMBERED.match(x)]
    if steps:
        lines.append("")
        lines += [f"{i}. {inline(s)}" for i, s in enumerate(steps[:MAX_STEPS], 1)]
        if len(steps) > MAX_STEPS:
            lines.append(f"(+{len(steps) - MAX_STEPS} more in the email)")

    alerts = [x for x in sections.get("ALERTS THE BOT IS WATCHING", []) if PRICE_ALERT.match(x) or TIME_ALERT.match(x)]
    actions = [x for x in alerts if (PRICE_ALERT.match(x) or TIME_ALERT.match(x)).groups()[-1].strip().upper()
               .startswith(("SELL", "BUY"))]
    lines.append("")
    if alerts:
        lines.append(f"Alerts: {len(alerts)} watched, {len(actions)} that ask you to act (/alerts for the list).")
    else:
        lines.append("Alerts: none watched.")
    lines.append("Full version in your email.")
    lines.append(NFA)
    return "\n".join(lines)


def changed_files(before: str, after: str) -> list[tuple[str, str]]:
    """(status, path) of analyses/*.md added or modified between two commits."""
    if not before or set(before) == {"0"}:
        out = subprocess.run(["git", "show", "--name-status", "--format=", after],
                             capture_output=True, text=True, check=True).stdout
    else:
        out = subprocess.run(["git", "diff", "--name-status", before, after],
                             capture_output=True, text=True, check=True).stdout
    files = []
    for row in out.splitlines():
        status, _, path = row.partition("\t")
        if status in ("A", "M") and re.fullmatch(r"analyses/\d{4}-\d\d-\d\d-(brief|event-[a-z]+)\.md", path):
            files.append((status, path))
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="")
    ap.add_argument("--after", default="HEAD")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    files = changed_files(args.before, args.after)
    if not files:
        print("tldr: no brief or event check in this push")
        return 0
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not args.dry_run and not (token and chat_id):
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        return 2
    session, failed = requests.Session(), False
    for status, path in files:
        with open(path) as f:
            text = message(f.read(), updated=status == "M")
        if args.dry_run:
            print(f"--- {path} ---\n{text}")
            continue
        try:
            telegram.send_message(session, token, chat_id, text, silent=quiet_hours.is_quiet(time.time()))
            print(f"tldr: sent for {path}")
        except telegram.TelegramError as exc:
            print(f"telegram: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
