"""Regenerate the Kraken fixtures: python tests/fixtures/make_fixtures.py

The files are in Kraken's exact wire format (prices as strings, the pair's
internal name as the result key, `last`, the open candle as the final row).
They are generated, not recorded: the session that built milestone 1 could
not reach api.kraken.com. Swap in real recordings any time; the tests only
rely on the scenario described next to each file below.

Clock: the heartbeat "now" in the tests is 2026-10-03 12:00:40 UTC.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
T = lambda s: int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())  # noqa: E731


def base(t: int) -> float:
    return 74600 + 150 * math.sin(t / 2220)


def row(t: int, o: float, h: float, l: float, c: float, vol: float = 0.85) -> list:
    vwap = (h + l + c) / 3
    return [t, f"{o:.1f}", f"{h:.1f}", f"{l:.1f}", f"{c:.1f}", f"{vwap:.1f}", f"{vol:.8f}", 37]


def candles(start: int, end: int, step: int, wicks: dict[int, tuple[str, float]] = {}) -> list:
    rows = []
    for t in range(start, end + 1, step):
        o, c = base(t), base(t + step)
        h, l = max(o, c) + 12, min(o, c) - 12
        if t in wicks:
            side, extreme = wicks[t]
            if side == "low":
                l = extreme
            else:
                h = extreme
        rows.append(row(t, o, h, l, c))
    return rows


def ohlc(rows: list, pair: str = "XXBTZEUR") -> dict:
    # `last` is the start of the newest committed candle (the row before the open one).
    return {"error": [], "result": {pair: rows, "last": rows[-2][0]}}


def write(name: str, body: dict) -> None:
    (HERE / name).write_text(json.dumps(body, separators=(",", ":")) + "\n")


def main() -> None:
    eur, usd = 74550.1, 84000.0  # implied EUR/USD 1.12677

    def tick(last: float) -> dict:
        return {
            "a": [f"{last + 0.1:.5f}", "1", "1.000"],
            "b": [f"{last - 0.1:.5f}", "2", "2.000"],
            "c": [f"{last:.5f}", "0.00120000"],
            "v": ["412.11", "1290.4"],
            "p": [f"{last:.5f}", f"{last:.5f}"],
            "t": [9123, 30111],
            "l": [f"{last - 900:.5f}", f"{last - 1400:.5f}"],
            "h": [f"{last + 600:.5f}", f"{last + 900:.5f}"],
            "o": f"{last - 200:.5f}",
        }

    # Ticker for XBTEUR,XBTUSD at the heartbeat's "now".
    write("ticker.json", {"error": [], "result": {"XXBTZEUR": tick(eur), "XXBTZUSD": tick(usd)}})

    start, now_open = T("2026-10-03T06:00:00"), T("2026-10-03T12:00:00")
    # Quiet morning: 06:00 to the open 12:00 candle, price 74,450 to 74,750, no alert touched.
    write("ohlc_1m_quiet.json", ohlc(candles(start, now_open, 60)))
    # Wick between runs: at 11:57 UTC a one-minute low of 72,760 (exit is 72,800), back above 74,400 by 12:00.
    write("ohlc_1m_wick.json", ohlc(candles(start, now_open, 60, {T("2026-10-03T11:57:00"): ("low", 72760.0)})))
    # Late run: the scheduler skipped runs; the exit was touched at 11:40 UTC (low 72,790).
    write("ohlc_1m_late.json", ohlc(candles(start, now_open, 60, {T("2026-10-03T11:40:00"): ("low", 72790.0)})))
    # Upside: at 11:58 a high of 77,100 (T1 is 77,050).
    write("ohlc_1m_spike.json", ohlc(candles(start, now_open, 60, {T("2026-10-03T11:58:00"): ("high", 77100.0)})))
    # Stale (cached) response: the newest candle is 11:50, ten minutes before now.
    write("ohlc_1m_stale.json", ohlc(candles(start, T("2026-10-03T11:50:00"), 60)))
    # 15-minute candles for the two days before, for alerts older than the 12-hour 1-minute window.
    # 2 Oct 18:30 UTC: low 72,700. 2 Oct 18:45: the candle an alert armed at 18:47 sits in, low 72,650.
    write("ohlc_15m.json", ohlc(candles(T("2026-10-01T12:00:00"), now_open, 900, {
        T("2026-10-02T18:30:00"): ("low", 72700.0),
        T("2026-10-02T18:45:00"): ("low", 72650.0),
        T("2026-10-02T21:00:00"): ("low", 72750.0),
    })))


if __name__ == "__main__":
    main()
