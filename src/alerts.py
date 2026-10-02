"""Load, validate and evaluate state/alerts.json (schema in SPEC.md)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.kraken import Candle

DIRECTIONS = ("below", "above")
KINDS = ("action", "watch")


class AlertsFileError(Exception):
    pass


def parse_ts(value: str | None) -> float | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise AlertsFileError(f"{path.name} can't be read ({type(exc).__name__})") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("alerts"), list):
        raise AlertsFileError(f"{path.name} has no 'alerts' list")
    return doc


def save(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def problems(doc: dict, now: float) -> list[str]:
    """Reasons an armed alert can't be watched. Those alerts are skipped."""
    out = []
    seen = set()
    for i, a in enumerate(doc["alerts"]):
        if not isinstance(a, dict):
            out.append(f"alert #{i + 1} is not an object")
            continue
        aid = a.get("id") or f"alert #{i + 1}"
        if aid in seen:
            out.append(f"{aid}: duplicate id")
        seen.add(aid)
        if a.get("status") != "armed":
            continue
        if not a.get("id"):
            out.append(f"{aid}: no id")
        if not isinstance(a.get("pair"), str) or not a["pair"]:
            out.append(f"{aid}: no pair")
        if a.get("direction") not in DIRECTIONS:
            out.append(f"{aid}: direction must be below or above")
        if isinstance(a.get("level"), bool) or not isinstance(a.get("level"), (int, float)):
            out.append(f"{aid}: level is not a number")
        if a.get("kind") not in KINDS:
            out.append(f"{aid}: kind must be action or watch")
        if not isinstance(a.get("message"), str) or not a["message"]:
            out.append(f"{aid}: no message")
        for field in ("armed_at", "valid_from", "valid_until"):
            try:
                parse_ts(a.get(field))
            except (TypeError, ValueError, AttributeError):
                out.append(f"{aid}: {field} is not an ISO time")
        try:
            if (parse_ts(a.get("armed_at")) or 0) > now + 300:
                out.append(f"{aid}: armed_at is in the future")
        except (TypeError, ValueError, AttributeError):
            pass
        band = a.get("guard_band")
        if band is not None and not (
            isinstance(band, list) and len(band) == 2 and all(isinstance(x, (int, float)) for x in band)
        ):
            out.append(f"{aid}: guard_band must be [low, high]")
    return out


def watchable(doc: dict, bad: list[str]) -> list[dict]:
    """Armed alerts with no validation problem."""
    bad_ids = {p.split(":", 1)[0] for p in bad}
    return [
        a for a in doc["alerts"]
        if isinstance(a, dict) and a.get("status") == "armed" and a.get("id") and a["id"] not in bad_ids
    ]


def eligible(candle: Candle, armed_ts: float) -> bool:
    """Does this candle hold only trades from after the alert was armed?

    The 1-minute candle the alert was armed in counts (seconds of overlap,
    and alerts are set away from the price). A coarser candle counts only if
    it starts at or after arming, so a 15-minute fill-in can never fire an
    alert on a wick from before it existed.
    """
    if candle.interval_s <= 60:
        return candle.time >= armed_ts - armed_ts % 60
    return candle.time >= armed_ts


def touches(alert: dict, candle: Candle) -> bool:
    if alert["direction"] == "below":
        return candle.low <= alert["level"]
    return candle.high >= alert["level"]


@dataclass
class Hit:
    alert: dict
    authorised: bool  # False: touched, but outside valid_from / valid_until
    first_touch: Candle
    extreme: float  # lowest low (below) or highest high (above) since first touch
    extreme_time: int


def evaluate(alert: dict, candles: list[Candle], now: float) -> Hit | None:
    """Has this armed alert been hit by any candle since it was armed?"""
    armed_ts = parse_ts(alert["armed_at"])
    valid_from = parse_ts(alert.get("valid_from"))
    valid_until = parse_ts(alert.get("valid_until"))

    def in_window(c: Candle) -> bool:
        return (valid_from is None or c.time >= valid_from) and (valid_until is None or c.time < valid_until)

    now_in_window = (valid_from is None or now >= valid_from) and (valid_until is None or now < valid_until)
    hits = [c for c in candles if eligible(c, armed_ts) and touches(alert, c)]
    if not hits:
        return None
    authorised_hits = [c for c in hits if in_window(c)] if now_in_window else []
    if authorised_hits:
        hits, authorised = authorised_hits, True
    elif alert.get("gate_notified_at"):
        return None  # already told him it was touched outside the window
    else:
        authorised = False
    if alert["direction"] == "below":
        ext = min(hits, key=lambda c: c.low)
        extreme = ext.low
    else:
        ext = max(hits, key=lambda c: c.high)
        extreme = ext.high
    return Hit(alert, authorised, hits[0], extreme, ext.time)
