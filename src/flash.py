"""Flash dip: Nuno's setup, tested in analyses/backtests/2026-10-19-flash-dip-vs-dip-setup.md.

BTC falls at least `drop` (5%) under its highest price of the last `window_h`
(4) hours. The heartbeat sees it within a run and sends a BUY message with the
plan. Nuno buys only if he can within about 15 minutes. When he reports the
buy (Done, then /bought; or /bought straight away), three exits are armed from
his entry: sell at +target, sell at -stop, sell after hold_h hours.

Guards: awake hours only (signals in quiet hours are skipped, as agreed), no
signal while a position is open or a flash buy is waiting, one signal per
window. Settings live in config/flash.json; docs/strategy.md has the rule.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src import alerts
from src.messages import LISBON, NFA, both, escape, lisbon

DEFAULTS = {
    "enabled": True,
    "pair": "XBTEUR",
    "window_h": 4,
    "drop": 0.05,
    "target": 0.02,
    "stop": 0.04,
    "hold_h": 24,
    "act_within_min": 15,
    "risk": 0.02,
    "cap": 0.40,
}
CONFIG = Path("config/flash.json")


def config(path: Path = CONFIG) -> dict:
    try:
        return {**DEFAULTS, **json.loads(path.read_text())}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def lookback_s(cfg: dict) -> int:
    return int(cfg["window_h"] * 3600)


def is_flash(alert: dict | None) -> bool:
    return bool(alert and isinstance(alert.get("flash"), dict))


def size_usd(account: dict | None, cfg: dict) -> float:
    """2% of the balance at risk on the stop distance, capped at 40% of the balance, in $10 steps."""
    balance = float((account or {}).get("cash_usd") or (account or {}).get("balance_usd") or 0)
    size = min(balance * cfg["risk"] / cfg["stop"], balance * cfg["cap"])
    return max(0.0, size // 10 * 10)


def detect(candles, last: float, now: float, cfg: dict) -> tuple[float, int] | None:
    """(high, time of the high) when the price is `drop` under the high of the window."""
    recent = [c for c in candles if c.time >= now - lookback_s(cfg)]
    if not recent:
        return None
    top = max(recent, key=lambda c: c.high)
    return (top.high, top.time) if last <= top.high * (1 - cfg["drop"]) else None


EXPIRE_S = 2 * 3600  # an unanswered buy lapses: the bounce is long gone


def expire_stale(doc: dict, now: float) -> list[str]:
    """Flash buys nobody answered within EXPIRE_S: marked skipped, so they stop blocking new signals."""
    out = []
    for a in doc["alerts"]:
        if is_flash(a) and a.get("status") == "fired" and now - (alerts.parse_ts(a.get("fired_at")) or now) > EXPIRE_S:
            a.update(status="skipped", skipped_at=alerts.iso(now), skipped_reason="no answer within 2 hours")
            out.append(a["id"])
    return out


def blocked(doc: dict, account: dict | None, hb: dict, now: float, cfg: dict) -> str | None:
    """Why no signal may go out now, or None."""
    if not cfg["enabled"]:
        return "switched off"
    if (account or {}).get("positions"):
        return "a position is open"
    for a in doc["alerts"]:
        if is_flash(a) and (a.get("status") == "fired" or a.get("awaiting_fill")):
            return "a flash buy is still waiting"
    last = alerts.parse_ts(hb.get("flash_signal_at"))
    if last is not None and now - last < lookback_s(cfg):
        return "already signalled in this window"
    return None


def level(price: float, up: bool) -> float:
    """EUR levels in EUR 50 steps (CLAUDE.md), rounded towards the entry so they fire, never later."""
    step = 50
    return (price // step) * step if up else -(-price // step) * step


def buy_alert(now: float, top: float, top_t: int, last: float, size: float, cfg: dict, eur_usd: float) -> dict:
    stamp = datetime.fromtimestamp(now, LISBON).strftime("%Y%m%d-%H%M")
    return {
        "id": f"flash-{stamp}",
        "pair": cfg["pair"],
        "direction": "time",  # a record of the signal; it is sent at once, never watched
        "at": alerts.iso(now),
        "level": None,
        "kind": "action",
        "trade": "buy",
        "message": f"BUY ${size:,.0f} of BTC at market now (flash dip).",
        "status": "fired",
        "armed_at": alerts.iso(now),
        "fired_at": alerts.iso(now),
        "fired_source": "kraken",
        "valid_from": None,
        "valid_until": None,
        "guard_band": None,
        "on_done": None,
        "flash": {
            "high_eur": round(top, 1), "high_at": alerts.iso(top_t), "signal_eur": round(last, 1),
            "fall": round(1 - last / top, 4), "size_usd": size, "eur_usd": round(eur_usd, 5),
            "target": cfg["target"], "stop": cfg["stop"], "hold_h": cfg["hold_h"],
            "act_within_min": cfg["act_within_min"],
        },
    }


def buy_message(a: dict, now: float) -> str:
    f = a["flash"]
    rate, entry = f["eur_usd"], f["signal_eur"]
    tgt, stop = level(entry * (1 + f["target"]), True), level(entry * (1 - f["stop"]), False)
    deadline = now + f["hold_h"] * 3600
    return "\n".join([
        f"<b>ACTION: {escape(a['message'])}</b>",
        f"BTC fell {f['fall']:.1%} in the last hours: from {both(f['high_eur'], 'EUR', rate)} "
        f"({lisbon(alerts.parse_ts(f['high_at']), now)}) to {both(entry, 'EUR', rate)} now (Kraken).",
        f"<b>Only buy if you can do it within {f['act_within_min']} minutes.</b> Later, the bounce is usually "
        "under way and the odds drop: then tap Not done and let this one go.",
        "",
        "The plan, from about this price (set from your actual buy price once you report it):",
        f"- Sell at +{f['target']:.0%}: about {both(tgt, 'EUR', rate)}",
        f"- Exit at -{f['stop']:.0%}: about {both(stop, 'EUR', rate)}",
        f"- Or sell after {f['hold_h']} hours: {lisbon(deadline, now)} Lisbon",
        "The bot sets all three alerts for you.",
        "",
        f"Tap Done once you've bought, then send /bought {f['size_usd']:.0f} at &lt;price&gt;.",
        NFA,
    ])


def exit_ids(buy: dict) -> list[str]:
    return [f"{buy['id']}-target", f"{buy['id']}-stop", f"{buy['id']}-time"]


def exit_alerts(buy: dict, entry_eur: float, now: float, rate: float) -> list[dict]:
    f = buy["flash"]
    base = buy["id"]
    ids = exit_ids(buy)
    tgt, stop = level(entry_eur * (1 + f["target"]), True), level(entry_eur * (1 - f["stop"]), False)
    common = {"pair": buy["pair"], "kind": "action", "trade": "sell_all", "status": "armed",
              "armed_at": alerts.iso(now), "valid_from": None, "valid_until": None, "guard_band": None,
              "flash_exit_of": base}

    def others(me: str) -> dict:
        return {"arm": [], "disarm": [i for i in ids if i != me]}

    return [
        {**common, "id": ids[0], "direction": "above", "level": tgt, "level_usd_ref": round(tgt * rate),
         "message": f"SELL ALL your BTC at market now: the flash-dip target (+{f['target']:.0%}) is reached.",
         "on_done": others(ids[0])},
        {**common, "id": ids[1], "direction": "below", "level": stop, "level_usd_ref": round(stop * rate),
         "message": f"SELL ALL your BTC at market now: the flash-dip exit (-{f['stop']:.0%}) is hit.",
         "on_done": others(ids[1])},
        {**common, "id": ids[2], "direction": "time", "level": None, "at": alerts.iso(now + f["hold_h"] * 3600),
         "message": f"SELL ALL your BTC at market now: {f['hold_h']} hours since the flash-dip buy.",
         "on_done": others(ids[2])},
    ]


def arm_exits(doc: dict, buy: dict, entry_eur: float, now: float, rate: float) -> list[str]:
    """Arm (or, with the real fill price, re-level) the three exits of a flash buy. Returns their ids."""
    new = exit_alerts(buy, entry_eur, now, rate)
    existing = {a.get("id"): a for a in doc["alerts"] if isinstance(a, dict)}
    for a in new:
        old = existing.get(a["id"])
        if old is None:
            doc["alerts"].append(a)
        elif old.get("status") == "armed":
            # Same alert, better price: move the level, keep armed_at and the 24h deadline.
            old.update({k: a[k] for k in ("level", "level_usd_ref") if a.get(k) is not None})
    buy.setdefault("flash", {})["entry_eur"] = round(entry_eur, 1)
    return [a["id"] for a in new]


def latest_buy(doc: dict | None) -> dict | None:
    """The newest flash buy that is waiting for a fill (fired, or done and awaiting the price)."""
    waiting = [a for a in (doc or {}).get("alerts", []) if is_flash(a)
               and (a.get("status") == "fired" or (a.get("status") == "done" and a.get("awaiting_fill")))]
    return max(waiting, key=lambda a: a.get("fired_at") or "", default=None)
