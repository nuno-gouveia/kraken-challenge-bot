"""Market snapshot for the daily brief (SPEC.md milestone 3): data/snapshot.json.

    python -m src.snapshot [--out data/snapshot.json]

Runs on GitHub Actions at 06:45 UTC (Claude's cloud sessions can't reach
Kraken). For BTC, ETH, LINK, BCH, DOGE and SHIB, in USD and EUR: last price,
24h high/low/change, 7d change, and daily RSI14, ATR14, EMA20/50/200,
Bollinger(20,2) and MACD(12,26,9), computed from CLOSED daily candles only.
Today's open candle is reported on its own.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from src import indicators as ind
from src import kraken

PAIRS = {
    "BTC": {"USD": "XBTUSD", "EUR": "XBTEUR"},
    "ETH": {"USD": "ETHUSD", "EUR": "ETHEUR"},
    "LINK": {"USD": "LINKUSD", "EUR": "LINKEUR"},
    "BCH": {"USD": "BCHUSD", "EUR": "BCHEUR"},
    "DOGE": {"USD": "XDGUSD", "EUR": "XDGEUR"},
    "SHIB": {"USD": "SHIBUSD", "EUR": "SHIBEUR"},
}
CALL_GAP_S = 1.1  # stay well inside Kraken's public rate limit


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def r(x: float | None, digits: int = 8) -> float | None:
    """Round to significant precision that suits both BTC (80,000) and SHIB (0.00001)."""
    if x is None:
        return None
    if x == 0:
        return 0.0
    return float(f"{x:.{digits}g}")


def pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 2)


def analyse(daily: list[kraken.Candle], hourly: list[kraken.Candle]) -> dict:
    """Everything for one pair. `daily` and `hourly` are oldest first, the last item the open candle."""
    if len(daily) < 30 or len(hourly) < 25:
        raise ValueError(f"not enough candles ({len(daily)} daily, {len(hourly)} hourly)")
    open_day, closed = daily[-1], daily[:-1]
    closes = [c.close for c in closed]
    highs = [c.high for c in closed]
    lows = [c.low for c in closed]
    last = hourly[-1].close
    day_24h = hourly[-24:]

    rsi = ind.rsi(closes)[-1]
    atr = ind.atr(highs, lows, closes)[-1]
    mid, up, lo = ind.bollinger(closes)
    line, sig, hist = ind.macd(closes)
    emas = {n: ind.ema(closes, n)[-1] for n in (20, 50, 200)}

    out = {
        "last": r(last),
        "change_24h_pct": pct(last, hourly[-25].open),
        "high_24h": r(max(c.high for c in day_24h)),
        "low_24h": r(min(c.low for c in day_24h)),
        "change_7d_pct": pct(last, closed[-8].close),
        "open_candle": {"date": day(open_day.time), "open": r(open_day.open), "high": r(open_day.high),
                        "low": r(open_day.low), "last": r(open_day.close)},
        "daily": {
            "last_closed_date": day(closed[-1].time),
            "last_close": r(closes[-1]),
            "closed_candles": len(closed),
            "rsi14": round(rsi, 2) if rsi is not None else None,
            "atr14": r(atr, 6),
            "atr14_pct": round(atr / closes[-1] * 100, 2) if atr else None,
            "ema20": r(emas[20]),
            "ema50": r(emas[50]),
            "ema200": r(emas[200]),
            "bollinger_20_2": {
                "middle": r(mid[-1]), "upper": r(up[-1]), "lower": r(lo[-1]),
                "width_pct": round((up[-1] - lo[-1]) / mid[-1] * 100, 2) if mid[-1] else None,
                "percent_b": round((closes[-1] - lo[-1]) / (up[-1] - lo[-1]), 3) if up[-1] != lo[-1] else None,
            },
            "macd_12_26_9": {"macd": r(line[-1], 6), "signal": r(sig[-1], 6), "histogram": r(hist[-1], 6)},
        },
    }
    return out


def build(session: requests.Session, now: float, sleep=time.sleep) -> dict:
    snap = {
        "fetched_at": iso(now),
        "source": "Kraken public API (OHLC 1440 and 60 minute)",
        "notes": "Daily indicators use closed UTC daily candles only; open_candle is today's, still moving. "
                 "change_24h_pct is against the open of the hourly candle 24 hours back; change_7d_pct against "
                 "the daily close seven days back.",
        "eur_usd": None,
        "assets": {},
        "errors": [],
    }
    first = True
    for asset, by_ccy in PAIRS.items():
        snap["assets"][asset] = {}
        for ccy, pair in by_ccy.items():
            try:
                if not first:
                    sleep(CALL_GAP_S)
                first = False
                daily = kraken.ohlc(session, pair, 1440)
                kraken.check_fresh(daily, now, max_age_s=86400 + 180)
                sleep(CALL_GAP_S)
                hourly = kraken.ohlc(session, pair, 60)
                kraken.check_fresh(hourly, now, max_age_s=3600 + 180)
                snap["assets"][asset][ccy] = {"pair": pair, **analyse(daily, hourly)}
            except (kraken.KrakenError, ValueError) as exc:
                snap["errors"].append(f"{pair}: {exc}")
                print(f"snapshot: {pair}: {exc}")
    btc = snap["assets"].get("BTC", {})
    if "USD" in btc and "EUR" in btc:
        snap["eur_usd"] = round(btc["USD"]["last"] / btc["EUR"]["last"], 5)
        snap["eur_usd_source"] = "Kraken XBTUSD last / XBTEUR last"
    return snap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/snapshot.json"))
    args = parser.parse_args(argv)
    snap = build(requests.Session(), time.time())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snap, indent=2) + "\n")
    ok = sum(len(v) for v in snap["assets"].values())
    print(f"snapshot: {ok} pairs, {len(snap['errors'])} errors, EUR/USD {snap['eur_usd']}")
    if snap["eur_usd"] is None:
        return 1  # no BTC price: the brief can't work from this
    return 0


if __name__ == "__main__":
    sys.exit(main())
