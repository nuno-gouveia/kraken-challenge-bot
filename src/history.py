"""BTC price history for backtesting trading ideas: data/history/.

    python -m src.history [--months 37] [--root data/history]

Runs on GitHub Actions (history.yml); Claude's cloud sessions can't reach the
exchanges. Downloads 1-hour and 15-minute candles for BTC/EUR and BTC/USDT from
Binance's public archive (data.binance.vision): about three years of history,
which Kraken's API does not serve (it returns the last 720 candles only).
Binance's BTC/EUR tracks Kraken's closely; Kraken's own last 720 hourly
candles are saved next to it so the difference can be checked.

One gzipped CSV per month: data/history/<SYMBOL>/<interval>/<YYYY-MM>.csv.gz,
rows "time,open,high,low,close,volume" with time in UTC epoch seconds (the
candle's open). Past months never change, so a rerun only adds new ones and
rewrites the current month. Research data only: alerts still fire on Kraken.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import sys
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from src import kraken

ARCHIVE = "https://data.binance.vision/data/spot"
SYMBOLS = ("BTCEUR", "BTCUSDT")
INTERVALS = ("1h", "15m")
KRAKEN_CHECK = {"XBTEUR": "kraken-XBTEUR", "XBTUSD": "kraken-XBTUSD"}


def months_back(today: date, n: int) -> list[str]:
    """The last n months up to and including this one, oldest first, as YYYY-MM."""
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


def to_seconds(ts: int) -> int:
    """Binance spot archives switched from milliseconds to microseconds in 2025."""
    return ts // 1_000_000 if ts > 10**14 else ts // 1000


def parse_zip(data: bytes) -> list[tuple]:
    rows = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            for r in csv.reader(io.TextIOWrapper(z.open(name), "utf-8")):
                if not r or not r[0].strip().isdigit():
                    continue  # some archives carry a header row
                rows.append((to_seconds(int(r[0])), r[1], r[2], r[3], r[4], r[5]))
    return rows


def write_month(path: Path, rows: list[tuple]) -> None:
    rows = sorted(set(rows))
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(("time", "open", "high", "low", "close", "volume"))
    w.writerows(rows)
    # mtime=0: the same rows give the same bytes, so an unchanged month is not a git change.
    path.write_bytes(gzip.compress(buf.getvalue().encode(), mtime=0))


def fetch(session: requests.Session, url: str) -> bytes | None:
    r = session.get(url, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.content


def month_rows(session: requests.Session, symbol: str, interval: str, month: str, today: date) -> list[tuple]:
    """A whole past month from the monthly archive; the current month from daily ones."""
    if month != today.strftime("%Y-%m"):
        data = fetch(session, f"{ARCHIVE}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip")
        return parse_zip(data) if data else []
    rows = []
    for day in range(1, today.day):  # today's file appears tomorrow
        d = f"{month}-{day:02d}"
        data = fetch(session, f"{ARCHIVE}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{d}.zip")
        if data:
            rows += parse_zip(data)
    return rows


def update(root: Path, months: int, session: requests.Session, today: date | None = None) -> list[str]:
    today = today or datetime.now(timezone.utc).date()
    current = today.strftime("%Y-%m")
    written = []
    for symbol in SYMBOLS:
        for interval in INTERVALS:
            for month in months_back(today, months):
                path = root / symbol / interval / f"{month}.csv.gz"
                if path.exists() and month != current:
                    continue  # past months never change
                rows = month_rows(session, symbol, interval, month, today)
                if rows:
                    write_month(path, rows)
                    written.append(str(path))
                else:
                    print(f"history: nothing for {symbol} {interval} {month}")
    return written


def kraken_check(root: Path, session: requests.Session) -> None:
    """Kraken's own last 720 hourly candles, to compare with Binance's."""
    for pair, name in KRAKEN_CHECK.items():
        candles = kraken.ohlc(session, pair, 60)
        rows = [(c.time, c.open, c.high, c.low, c.close, "") for c in candles]
        write_month(root / name / "1h" / "last-720.csv.gz", rows)
        time.sleep(1.1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--months", type=int, default=37)
    ap.add_argument("--root", type=Path, default=Path("data/history"))
    args = ap.parse_args(argv)
    session = requests.Session()
    written = update(args.root, args.months, session)
    try:
        kraken_check(args.root, session)
    except kraken.KrakenError as exc:
        print(f"history: Kraken check skipped ({exc})")
    print(f"history: wrote {len(written)} month files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
