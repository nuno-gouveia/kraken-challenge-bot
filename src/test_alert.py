"""Arm a test alert a small step from the live Kraken price (SPEC.md milestone 1 acceptance).

    python -m src.test_alert --direction below [--pct 0.1] [--kind watch]

Adds one alert to state/alerts.json, armed now. A later heartbeat fires it
once; every run after that must leave it alone. The message says it's a
test, so Nuno knows there is nothing to do.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

from src import alerts, kraken


def build(price_eur: float, eur_usd: float, direction: str, pct: float, kind: str, now: float) -> dict:
    step = price_eur * pct / 100
    level = round(price_eur - step if direction == "below" else price_eur + step)
    stamp = alerts.iso(now)
    return {
        "id": f"test-{stamp[:16].replace(':', '').replace('-', '')}",
        "pair": "XBTEUR",
        "direction": direction,
        "level": level,
        "level_usd_ref": round(level * eur_usd),
        "kind": kind,
        "message": f"TEST alert, nothing to do. BTC moved {pct:g}% {'down' if direction == 'below' else 'up'} "
                   "from when the test was set; this checks the heartbeat reaches you.",
        "status": "armed",
        "armed_at": stamp,
        "valid_from": None,
        "valid_until": None,
        "guard_band": None,
        "on_done": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=alerts.DIRECTIONS, required=True)
    parser.add_argument("--pct", type=float, default=0.1)
    parser.add_argument("--kind", choices=alerts.KINDS, default="watch")
    parser.add_argument("--state-dir", type=Path, default=Path("state"))
    args = parser.parse_args(argv)

    last = kraken.ticker_last(requests.Session(), ["XBTEUR", "XBTUSD"])
    alert = build(last["XBTEUR"], last["XBTUSD"] / last["XBTEUR"], args.direction, args.pct, args.kind, time.time())
    path = args.state_dir / "alerts.json"
    doc = alerts.load(path)
    doc["alerts"].append(alert)
    alerts.save(path, doc)
    print(f"armed {alert['id']}: {alert['direction']} EUR {alert['level']:,} (price EUR {last['XBTEUR']:,.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
