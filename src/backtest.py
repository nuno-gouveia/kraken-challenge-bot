"""Backtest trading ideas on data/history (src/history.py). Research only.

    python -m src.backtest [--symbol BTCEUR] [--out analyses/backtests/NAME.md]

Two families, run on the same candles with the same costs and the same
challenge sizing (docs/strategy.md), so they can be compared:

- flash dip (Nuno, 19 Oct 2026): BTC falls X% from its high of the last W
  hours; buy shortly after; sell at a target, at a stop, or after H hours.
- dip setup (docs/strategy.md as of Oct 2026): sharp drop, oversold,
  stabilisation, buy; stop 1.2 ATR, T1 sells half and moves the exit to
  breakeven, T2. Plus a simplified Plan B breakout.

Costs per round trip: fee on both sides (zero on Kraken Funded) plus slippage on the exit. When a
candle touches both the stop and the target, the stop is assumed first.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

LISBON = ZoneInfo("Europe/Lisbon")
FEE = 0.0         # Kraken Funded: no trading commissions in the challenge or funded state (Nuno, 19 Oct 2026)
EXIT_SLIP = 0.003  # docs/strategy.md: assume 0.3% on an exit
START, TARGET, FLOOR = 1050.0, 1120.0, 950.0
RISK, CAP = 0.02, 0.40  # 2% of balance at risk; 40% of balance max per position


@dataclass
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float


@dataclass
class Trade:
    entry_t: int
    exit_t: int
    entry: float
    gross: float  # price return, before costs, weighted for partial exits
    stop_pct: float  # distance to the initial stop, for sizing
    why: str

    @property
    def net(self) -> float:
        return self.gross - 2 * FEE - EXIT_SLIP


def load(root: Path, symbol: str, interval: str) -> list[Bar]:
    bars = []
    for f in sorted((root / symbol / interval).glob("*.csv.gz")):
        rows = csv.reader(gzip.decompress(f.read_bytes()).decode().splitlines())
        next(rows, None)
        bars += [Bar(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in rows]
    bars.sort(key=lambda b: b.t)
    return bars


def quiet(t: int) -> bool:
    lt = datetime.fromtimestamp(t, LISBON)
    m = lt.hour * 60 + lt.minute
    return m >= 22 * 60 + 30 or m < 6 * 60 + 30


# ---- flash dip ----------------------------------------------------------------

@dataclass(frozen=True)
class Flash:
    window_h: int    # look back this many hours for the high
    drop: float      # signal when close is this far under that high (0.04 = 4%)
    target: float    # sell at entry * (1 + target)
    stop: float      # sell at entry * (1 - stop)
    hold_h: int = 24  # or after this many hours
    delay_bars: int = 1  # enter at the close of the bar after the signal (15m bars: ~15 to 30 min)
    skip_quiet: bool = False

    def label(self) -> str:
        return (f"fall {self.drop:.0%} in {self.window_h}h, target +{self.target:.1%}, "
                f"stop -{self.stop:.0%}, max {self.hold_h}h" + (", awake hours only" if self.skip_quiet else ""))


def rolling_high(bars: list[Bar], w: int) -> list[float]:
    """top[i] = highest high of bars[i - w + 1 .. i]."""
    from collections import deque
    top, dq = [], deque()
    for i, b in enumerate(bars):
        while dq and bars[dq[-1]].h <= b.h:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - w:
            dq.popleft()
        top.append(bars[dq[0]].h)
    return top


def flash_dip(bars: list[Bar], p: Flash, tops: dict[int, list[float]] | None = None) -> list[Trade]:
    step = bars[1].t - bars[0].t
    w = max(1, p.window_h * 3600 // step)
    top = (tops or {}).get(w) or rolling_high(bars, w)
    hold = p.hold_h * 3600 // step
    trades, i = [], w
    while i < len(bars) - p.delay_bars - 1:
        if bars[i].c > top[i] * (1 - p.drop):
            i += 1
            continue
        k = i + p.delay_bars
        if p.skip_quiet and quiet(bars[k].t):
            i += 1
            continue
        entry = bars[k].c
        stop, tgt = entry * (1 - p.stop), entry * (1 + p.target)
        exit_px, why, end = None, "time", min(k + hold, len(bars) - 1)
        for m in range(k + 1, end + 1):
            if bars[m].l <= stop:
                exit_px, why, end = stop, "stop", m
                break
            if bars[m].h >= tgt:
                exit_px, why, end = tgt, "target", m
                break
        if exit_px is None:
            exit_px = bars[end].c
        trades.append(Trade(bars[k].t, bars[end].t, entry, exit_px / entry - 1, p.stop, why))
        i = end + w  # one position at a time; the next signal needs a fresh window after the exit
    return trades


# ---- dip setup and Plan B (daily) --------------------------------------------

def daily(hourly: list[Bar]) -> list[Bar]:
    days: dict[int, list[Bar]] = {}
    for b in hourly:
        days.setdefault(b.t - b.t % 86400, []).append(b)
    return [Bar(d, v[0].o, max(x.h for x in v), min(x.l for x in v), v[-1].c)
            for d, v in sorted(days.items()) if len(v) >= 20]


def rsi_atr(days: list[Bar], n: int = 14) -> tuple[list[float | None], list[float | None]]:
    rsi: list[float | None] = [None] * len(days)
    atr: list[float | None] = [None] * len(days)
    gain = loss = tr_avg = 0.0
    for i in range(1, len(days)):
        ch = days[i].c - days[i - 1].c
        tr = max(days[i].h - days[i].l, abs(days[i].h - days[i - 1].c), abs(days[i].l - days[i - 1].c))
        if i <= n:
            gain += max(ch, 0) / n
            loss += max(-ch, 0) / n
            tr_avg += tr / n
        else:
            gain = (gain * (n - 1) + max(ch, 0)) / n
            loss = (loss * (n - 1) + max(-ch, 0)) / n
            tr_avg = (tr_avg * (n - 1) + tr) / n
        if i >= n:
            rsi[i] = 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
            atr[i] = tr_avg
    return rsi, atr


@dataclass(frozen=True)
class Dip:
    rsi_below: float
    drop_atr: float = 1.5   # step 1: fall of this many ATR within two days
    expire_days: int = 3    # step 1 expires
    stop_atr: float = 1.2
    t1_atr: float = 1.2
    t2_atr: float = 2.4
    breakout: bool = False  # Plan B breakout instead: close above the 20-day high

    def label(self) -> str:
        if self.breakout:
            return f"Plan B breakout: close above 20-day high, stop {self.stop_atr} ATR, T1 {self.t1_atr}, T2 {self.t2_atr} ATR"
        return (f"dip setup: fall {self.drop_atr} ATR in 2 days, RSI below {self.rsi_below:g}, "
                f"stabilise, stop {self.stop_atr} ATR, T1 {self.t1_atr} / T2 {self.t2_atr} ATR")


def dip_setup(hourly: list[Bar], p: Dip) -> list[Trade]:
    days = daily(hourly)
    rsi, atr = rsi_atr(days)
    by_t = {b.t: i for i, b in enumerate(hourly)}
    trades, armed_at, d = [], None, 15
    while d < len(days) - 1:
        a = atr[d - 1]
        if a is None:
            d += 1
            continue
        if p.breakout:
            hi20 = max(x.h for x in days[d - 20:d]) if d >= 20 else None
            go = hi20 is not None and days[d].c > hi20
        else:
            if days[d - 2].c - days[d].c >= p.drop_atr * a and (rsi[d] or 100) < p.rsi_below:
                armed_at = d  # steps 1 and 2 on this close
            go = (armed_at is not None and d > armed_at and d - armed_at <= p.expire_days
                  and days[d].l >= days[d - 1].l and days[d].c > days[d - 1].c)  # step 3: no new low, up close
        if not go:
            d += 1
            continue
        armed_at = None
        k = by_t.get(days[d + 1].t)
        if k is None:
            d += 1
            continue
        entry, a = hourly[k].o, atr[d]
        stop, t1, t2 = entry - p.stop_atr * a, entry + p.t1_atr * a, entry + p.t2_atr * a
        half_done, realised, end, why = False, 0.0, None, "time"
        for m in range(k, min(k + 24 * 20, len(hourly))):  # give up after 20 days
            b = hourly[m]
            if b.l <= stop:
                realised += (0.5 if half_done else 1.0) * (stop / entry - 1)
                end, why = m, ("breakeven" if half_done else "stop")
                break
            if not half_done and b.h >= t1:
                realised += 0.5 * (t1 / entry - 1)
                half_done, stop = True, entry
            if half_done and b.h >= t2:
                realised += 0.5 * (t2 / entry - 1)
                end, why = m, "T2"
                break
        if end is None:
            end = min(k + 24 * 20, len(hourly)) - 1
            realised += (0.5 if half_done else 1.0) * (hourly[end].c / entry - 1)
        trades.append(Trade(hourly[k].t, hourly[end].t, entry, realised, p.stop_atr * a / entry, why))
        while d < len(days) and days[d].t <= hourly[end].t:
            d += 1
    return trades


# ---- scoring -------------------------------------------------------------------

@dataclass
class Score:
    label: str
    trades: list[Trade]
    balance: float = START
    peak: float = START
    max_dd: float = 0.0
    passed_at: int | None = None
    failed_at: int | None = None
    per_year: dict[int, tuple[int, float]] = field(default_factory=dict)

    def run(self) -> "Score":
        for tr in self.trades:
            size = min(self.balance * RISK / max(tr.stop_pct, 1e-6), self.balance * CAP)
            self.balance += size * tr.net
            self.peak = max(self.peak, self.balance)
            self.max_dd = max(self.max_dd, 1 - self.balance / self.peak)
            if self.passed_at is None and self.failed_at is None:
                if self.balance >= TARGET:
                    self.passed_at = tr.exit_t
                elif self.balance <= FLOOR:
                    self.failed_at = tr.exit_t
            y = datetime.fromtimestamp(tr.entry_t, timezone.utc).year
            n, s = self.per_year.get(y, (0, 0.0))
            self.per_year[y] = (n + 1, s + tr.net)
        return self

    @property
    def n(self) -> int:
        return len(self.trades)

    @property
    def win(self) -> float:
        return sum(t.net > 0 for t in self.trades) / self.n if self.n else 0.0

    @property
    def avg(self) -> float:
        return mean(t.net for t in self.trades) if self.n else 0.0

    @property
    def worst(self) -> float:
        return min((t.net for t in self.trades), default=0.0)


def day(t: int | None) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%d %b %Y") if t else "never"


def flash_grid(skip_quiet: bool) -> list[Flash]:
    return [Flash(w, x, tg, st, 24, 1, skip_quiet)
            for w, x, tg, st in itertools.product((1, 2, 3, 4, 6), (0.03, 0.04, 0.05, 0.06),
                                                  (0.01, 0.015, 0.02, 0.03), (0.02, 0.03, 0.04))]


def report(symbol: str, root: Path) -> str:
    m15, h1 = load(root, symbol, "15m"), load(root, symbol, "1h")
    span = f"{day(h1[0].t)} to {day(h1[-1].t)}"
    out = [f"# Backtest: flash dip vs dip setup ({symbol}, {span})", "",
           f"Costs per round trip: fee {FEE:.2%} each side plus {EXIT_SLIP:.1%} exit slippage "
           f"({2 * FEE + EXIT_SLIP:.1%}). Sizing: 2% of balance at risk, at most 40% of balance per position. "
           f"Challenge start ${START:,.0f}, pass ${TARGET:,.0f}, fail ${FLOOR:,.0f}. "
           "Returns per trade are after costs. Source: Binance archive (research only).", ""]

    def table(title: str, scores: list[Score]) -> None:
        out.extend([f"## {title}", "",
                    "| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |",
                    "|---|---|---|---|---|---|---|---|---|"])
        for s in scores:
            out.append(f"| {s.label} | {s.n} | {s.win:.0%} | {s.avg:+.2%} | {s.worst:+.2%} | ${s.balance:,.0f} | "
                       f"{s.max_dd:.1%} | {day(s.passed_at)} | {day(s.failed_at)} |")
        out.append("")

    def years(s: Score) -> str:
        return ", ".join(f"{y}: {n} trades, {tot / n:+.2%} avg" for y, (n, tot) in sorted(s.per_year.items()))

    step = m15[1].t - m15[0].t
    tops = {w * 3600 // step: rolling_high(m15, w * 3600 // step) for w in (1, 2, 3, 4, 6)}
    for skip in (False, True):
        scores = [Score(p.label(), flash_dip(m15, p, tops)).run() for p in flash_grid(skip)]
        scores = [s for s in scores if s.n >= 10]
        scores.sort(key=lambda s: s.avg * s.n, reverse=True)
        table(f"Flash dip: best 10 of {len(flash_grid(skip))} variants"
              + (" (signals in quiet hours skipped)" if skip else " (all hours)"), scores[:10])
        if scores:
            out.append(f"Best by year: {years(scores[0])}.")
            out.append("")

    sensitivity(m15, out)

    dips = [Score(p.label(), dip_setup(h1, p)).run()
            for p in (Dip(30), Dip(45), Dip(60), Dip(100, breakout=True))]
    table("Current rules: dip setup (three readings of 'oversold') and Plan B breakout", dips)
    for s in dips:
        if s.n:
            out.append(f"- {s.label}: {years(s)}.")
    out.append("")
    return "\n".join(out)


def sensitivity(m15: list[Bar], out: list[str]) -> None:
    """The leading rules under other costs and slower reactions: the edge is thin."""
    global FEE, EXIT_SLIP
    saved = FEE, EXIT_SLIP
    rules = [Flash(4, 0.05, 0.02, 0.04), Flash(4, 0.05, 0.015, 0.03), Flash(1, 0.05, 0.015, 0.04)]
    out.extend(["## How fast you buy, and slippage, decide the result", "",
                "Balance after three years for the leading rules, by round-trip cost and by how long after the "
                "signal the buy happens.", "",
                "| Rule | Cost | Buy after 15 min | 30 min | 60 min |", "|---|---|---|---|---|"])
    for rule in rules:
        for fee, slip in ((0.0, 0.003), (0.0, 0.005), (0.004, 0.003)):
            FEE, EXIT_SLIP = fee, slip
            cells = []
            for delay in (1, 2, 4):
                q = Flash(rule.window_h, rule.drop, rule.target, rule.stop, 24, delay)
                sc = Score(q.label(), flash_dip(m15, q)).run()
                cells.append(f"${sc.balance:,.0f} ({sc.n} trades, {sc.win:.0%} won)")
            out.append(f"| {rule.label()} | {2 * fee + slip:.2%} | " + " | ".join(cells) + " |")
    FEE, EXIT_SLIP = saved
    out.append("")
    out.extend(["Before costs: how often a buy after the fall reached +1.5% before falling another 4% (15 min delay).", "",
                "| Fall | Within | Events | Bounced +1.5% first | Stopped | Neither in 24h |", "|---|---|---|---|---|---|"])
    for x in (0.03, 0.04, 0.05, 0.06):
        for w in (1, 3, 6):
            t = flash_dip(m15, Flash(w, x, 0.015, 0.04))
            out.append(f"| {x:.0%} | {w}h | {len(t)} | {sum(z.why == 'target' for z in t)} | "
                       f"{sum(z.why == 'stop' for z in t)} | {sum(z.why == 'time' for z in t)} |")
    out.append("")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCEUR")
    ap.add_argument("--root", type=Path, default=Path("data/history"))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    text = report(args.symbol, args.root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
