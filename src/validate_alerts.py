"""Check an alerts file before committing it (the daily brief runs this).

    python -m src.validate_alerts [state/alerts.json]

Errors (exit 1) are things the heartbeat would refuse or misread. Warnings
are house rules worth a second look.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from src import alerts, quiet_hours

EM_DASH = "\u2014"


def check(doc: dict, now: float) -> tuple[list[str], list[str]]:
    errors = alerts.problems(doc, now)
    warnings = []
    ids = set()
    for a in doc["alerts"]:
        if not isinstance(a, dict):
            continue
        aid = a.get("id", "?")
        ids.add(aid)
        if EM_DASH in str(a.get("message", "")):
            errors.append(f"{aid}: message has an em dash")
        if a.get("status") not in ("armed", "held", "fired", "done", "skipped", "disabled"):
            errors.append(f"{aid}: unknown status {a.get('status')!r}")
        if a.get("status") != "armed":
            continue
        if a.get("pair", "").endswith("EUR") and isinstance(a.get("level"), (int, float)) and a["level"] % 50:
            warnings.append(f"{aid}: EUR level {a['level']} is not a multiple of 50")
        if alerts.is_timed(a):
            try:
                at = alerts.parse_ts(a.get("at"))
            except (TypeError, ValueError, AttributeError):
                at = None
            if at is not None and at <= now:
                warnings.append(f"{aid}: at is in the past, it fires on the next heartbeat")
            if at is not None and a.get("kind") == "action" and quiet_hours.is_quiet(at):
                warnings.append(f"{aid}: at falls in quiet hours (22:30 to 06:30 Lisbon), it waits until 06:30")
        elif "level_usd_ref" not in a:
            warnings.append(f"{aid}: no level_usd_ref")
        if a.get("kind") == "action":
            trade = alerts.trade_of(a)
            if trade == "none":
                warnings.append(f"{aid}: action alert whose message doesn't start with BUY or SELL and has no trade field")
            if trade == "buy" and not a.get("guard_band"):
                warnings.append(f"{aid}: entry alert without a guard_band")
    for a in doc["alerts"]:
        if not isinstance(a, dict):
            continue
        for key in ("arm", "disarm"):
            for target in (a.get("on_done") or {}).get(key, []):
                if target not in ids:
                    errors.append(f"{a.get('id')}: on_done.{key} names unknown alert {target}")
    if EM_DASH in str(doc.get("note", "")):
        errors.append("note has an em dash")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    path = Path((argv or sys.argv[1:] or ["state/alerts.json"])[0])
    try:
        doc = alerts.load(path)
    except alerts.AlertsFileError as exc:
        print(f"ERROR {exc}")
        return 1
    errors, warnings = check(doc, time.time())
    for e in errors:
        print(f"ERROR {e}")
    for w in warnings:
        print(f"warning {w}")
    armed = sum(1 for a in doc["alerts"] if isinstance(a, dict) and a.get("status") == "armed")
    print(f"{path}: {armed} armed, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
