"""Backtest of a more active, more aggressive challenge strategy. Research only.

    python -m src.backtest_active [--out analyses/backtests/NAME.md]

Nuno, 12 Nov 2026: the money is virtual, the current rule barely trades, be
more aggressive. This asks three things of data/history (15-minute candles):

1. Which dip trigger trades more often and still has an edge?
2. How big can a position be, given the $950 floor?
3. How does that compare with one all-in swing?

It is stricter than src/backtest.py on two points that matter once positions
get big:

- Quiet hours (22:30 to 06:30 Lisbon) are modelled: no buys, and an exit due
  at night happens at the 06:30 price, as the bot does it.
- A challenge run fails when the equity touches the floor inside a trade (the
  worst price of the trade, nights included), and passes when it touches the
  target, not only on the closed balance.

A challenge is started every week of the history that has a full year of data
ahead of it, from today's balance. Those runs overlap, so the percentages
describe the history; they are not independent trials.
"""

from __future__ import annotations

import argparse
import random
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from src.backtest import Bar, load, quiet, rolling_high

SLIP = 0.003                # docs/strategy.md: 0.3% on an exit; no fees on Kraken Funded
START, TARGET, FLOOR = 1050.60, 1120.0, 950.0
BARS_H = 4                  # 15-minute candles
YEAR_S = 365 * 86400
SYMBOLS = ("BTCEUR", "BTCUSDT")


@dataclass
class Market:
    symbol: str
    bars: list[Bar]
    asleep: list[bool]      # the candle opens in quiet hours (the first awake one opens at 06:30)

    def __post_init__(self) -> None:
        self._tops: dict[int, list[float]] = {}

    def top(self, hours: int) -> list[float]:
        if hours not in self._tops:
            self._tops[hours] = rolling_high(self.bars, hours * BARS_H)
        return self._tops[hours]

    def dips(self, hours: int, drop: float) -> list[int]:
        """Candles that close `drop` under the high of the last `hours`, awake hours only."""
        top = self.top(hours)
        return [i for i, b in enumerate(self.bars) if b.c <= top[i] * (1 - drop) and not self.asleep[i]]


def market(root: Path, symbol: str) -> Market:
    bars = load(root, symbol, "15m")
    return Market(symbol, bars, [quiet(b.t) for b in bars])


@dataclass
class Trade:
    k: int        # entry candle
    m: int        # exit candle
    net: float    # return after slippage
    mae: float    # worst price against the entry while the trade was open, nights included
    mfe: float    # best price in awake hours before the exit
    why: str


@dataclass(frozen=True)
class Rule:
    hours: int = 6
    drop: float = 0.04
    target: float = 0.02
    stop: float = 0.04
    hold_h: int = 24
    delay: int = 1          # buy at the close of the candle after the signal (15 to 30 minutes)
    slip: float = SLIP

    def label(self) -> str:
        return (f"fall {self.drop:.1%} in {self.hours}h, +{self.target:.1%} / -{self.stop:.0%} / {self.hold_h}h"
                .replace(".0%", "%"))


def one_trade(mk: Market, k: int, target: float, stop: float, hold: int, slip: float) -> Trade:
    """Buy at the close of candle k; sell at the target, the stop or after `hold` candles.
    At night nothing is sold: the first candle from 06:30 acts on its opening price."""
    bars, asleep = mk.bars, mk.asleep
    entry = bars[k].c
    stp, tgt = entry * (1 - stop), entry * (1 + target)
    mae = mfe = 0.0
    end, m, last = min(k + hold, len(bars) - 1), k + 1, len(bars) - 1
    while m <= last:
        b = bars[m]
        mae = min(mae, b.l / entry - 1)
        if asleep[m]:
            m += 1
            continue
        if asleep[m - 1]:   # 06:30: every exit due overnight is re-checked against the price now
            if b.o <= stp:
                return Trade(k, m, b.o / entry - 1 - slip, mae, mfe, "stop at 06:30")
            if b.o >= tgt:
                return Trade(k, m, b.o / entry - 1 - slip, mae, max(mfe, b.o / entry - 1), "target at 06:30")
            if m > end:
                return Trade(k, m, b.o / entry - 1 - slip, mae, mfe, "time")
        if b.l <= stp:      # stop and target in one candle: the stop is assumed first
            return Trade(k, m, min(stp, b.o) / entry - 1 - slip, mae, mfe, "stop")
        if b.h >= tgt:
            return Trade(k, m, target - slip, mae, max(mfe, target), "target")
        mfe = max(mfe, b.h / entry - 1)
        if m >= end:
            return Trade(k, m, b.c / entry - 1 - slip, mae, mfe, "time")
        m += 1
    return Trade(k, last, bars[last].c / entry - 1 - slip, mae, mfe, "end of data")


def trades(mk: Market, r: Rule) -> list[Trade]:
    out, free_from = [], 0
    for i in mk.dips(r.hours, r.drop):
        k = i + r.delay
        if i < free_from or k >= len(mk.bars) - 2 or mk.asleep[k]:
            continue
        t = one_trade(mk, k, r.target, r.stop, r.hold_h * BARS_H, r.slip)
        out.append(t)
        free_from = t.m + r.hours * BARS_H   # one position at a time, then a fresh window
    return out


# ---- sizing --------------------------------------------------------------------

def fixed(share: float):
    return lambda balance, stop: balance * share


def cushion(share: float):
    """Risk `share` of the room above the floor on the stop; never more than the whole balance."""
    return lambda balance, stop: min(balance, share * (balance - FLOOR) / (stop + SLIP))


@dataclass
class Runs:
    n: int
    passed: list[float]     # days to pass
    failed: int

    def cell(self) -> str:
        p = len(self.passed) / self.n
        in90 = sum(d <= 90 for d in self.passed) / self.n
        days = f"{median(self.passed):.0f}" if self.passed else "n/a"
        return f"{p:.0%} | {self.failed / self.n:.0%} | {1 - p - self.failed / self.n:.0%} | {in90:.0%} | {days}"


def challenge(mk: Market, tr: list[Trade], size_of, stop: float, slip: float = SLIP) -> Runs:
    """A challenge from every week that has a year of history ahead; each runs for at most a year."""
    t0, t1 = mk.bars[0].t, mk.bars[-1].t
    entries = [mk.bars[t.k].t for t in tr]
    passed, failed, n, s = [], 0, 0, t0
    while s < t1 - YEAR_S:
        n += 1
        bal, j = START, bisect_left(entries, s)
        while j < len(tr) and entries[j] < s + YEAR_S:
            t = tr[j]
            j += 1
            size = size_of(bal, stop)
            if bal + size * t.mae <= FLOOR:
                failed += 1
                break
            if bal + size * (t.mfe - slip) >= TARGET or bal + size * t.net >= TARGET:
                passed.append((mk.bars[t.m].t - s) / 86400)
                break
            bal += size * t.net
            if bal <= FLOOR:
                failed += 1
                break
        s += 7 * 86400
    return Runs(n, passed, failed)


# ---- report --------------------------------------------------------------------

def year_of(mk: Market, t: Trade) -> int:
    return datetime.fromtimestamp(mk.bars[t.k].t, timezone.utc).year


def stats_row(label: str, mk: Market, tr: list[Trade]) -> str:
    if not tr:
        return f"| {label} | {mk.symbol} | 0 | | | | | |"
    span = (mk.bars[-1].t - mk.bars[0].t) / YEAR_S
    by_year = " / ".join(
        f"{mean(x):+.2%}" if (x := [t.net for t in tr if year_of(mk, t) == y]) else "n/a" for y in (2024, 2025, 2026))
    return (f"| {label} | {mk.symbol} | {len(tr) / span:.0f} | {sum(t.net > 0 for t in tr) / len(tr):.0%} | "
            f"{mean(t.net for t in tr):+.2%} | {by_year} | {min(t.net for t in tr):+.1%} | {min(t.mae for t in tr):+.1%} |")


STATS_HEAD = ["| Rule | Pair | Trades a year | Win | Avg per trade | Avg 2024 / 2025 / 2026 | Worst trade | Worst dip while held |",
              "|---|---|---|---|---|---|---|---|"]
RUNS_HEAD = ["| Sizing | First trade | Pair | Passed | Failed | Still open | Passed within 90 days | Median days to pass |",
             "|---|---|---|---|---|---|---|---|"]


def swing(mk: Market, share: float, stop_equity: float) -> str:
    """One all-in style position, bought twice a week through the history: pass or stop."""
    size = START * share
    target, stop = (TARGET - START) / size + SLIP, (START - stop_equity) / size - SLIP
    res, k, last = [], 5 * 96, len(mk.bars) - 60 * 96
    while k < last:
        j = k
        while mk.asleep[j]:
            j += 1
        t = one_trade(mk, j, target, stop, 120 * 96, SLIP)
        days = (mk.bars[t.m].t - mk.bars[j].t) / 86400
        res.append(("floor" if START + size * t.mae <= FLOOR else t.why.split(" ")[0], days))
        k += 336   # 3.5 days
    share_of = lambda w: sum(r[0] == w for r in res) / len(res)
    days_of = lambda w: median([r[1] for r in res if r[0] == w] or [0])
    return (f"| {share:.0%} of the balance, sell if equity falls to ${stop_equity:,.0f} | {mk.symbol} | {share_of('target'):.0%} | "
            f"{days_of('target'):.0f} | {share_of('stop'):.0%} | {share_of('floor'):.0%} |")


def worst_nights(mk: Market) -> tuple[int, float, int]:
    """Nights, the worst fall from the 22:30 price to the night's low, and how many nights fell over 5%."""
    falls, i = [], 1
    while i < len(mk.bars):
        if mk.asleep[i] and not mk.asleep[i - 1]:
            ref, low = mk.bars[i - 1].c, mk.bars[i - 1].c
            while i < len(mk.bars) and mk.asleep[i]:
                low = min(low, mk.bars[i].l)
                i += 1
            falls.append(low / ref - 1)
        else:
            i += 1
    return len(falls), min(falls), sum(f < -0.05 for f in falls)


def report(root: Path) -> str:
    mks = [market(root, s) for s in SYMBOLS]
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%d %b %Y")
    out = [f"# Backtest: a more active, more aggressive strategy ({day(mks[0].bars[0].t)} to {day(mks[0].bars[-1].t)})", "",
           f"BTC, 15-minute candles (Binance archive, research only). Exit slippage {SLIP:.1%}, no fees. Quiet hours "
           "22:30 to 06:30 Lisbon are modelled: no buys, and an exit due at night happens at the 06:30 price. "
           f"Challenge runs start at ${START:,.2f}, pass at ${TARGET:,.0f}, fail when equity touches ${FLOOR:,.0f} "
           "(inside a trade too). One run starts every week of the history and lasts at most a year; the runs overlap, "
           "so read the percentages as a description of the past three years, not as odds.", ""]

    current, proposed = Rule(4, 0.05), Rule(6, 0.04)
    out += ["## 1. Which trigger trades more often and still has an edge", "",
            "Every rule: buy 15 to 30 minutes after the signal, awake hours only, sell at +2%, at -4% or after 24 hours.", ""]
    out += STATS_HEAD
    for hours, drop in ((4, 0.05), (6, 0.05), (4, 0.04), (6, 0.04), (6, 0.035), (4, 0.03), (6, 0.03), (2, 0.02)):
        r = Rule(hours, drop)
        tag = " (today)" if r == current else " (proposed)" if r == proposed else ""
        for mk in mks:
            out.append(stats_row(f"fall {drop:.1%} in {hours}h{tag}".replace(".0%", "%"), mk, trades(mk, r)))
    out.append("")

    out += ["## 2. The exits around the proposed trigger (fall 4% in 6h)", ""] + STATS_HEAD
    for tg, st, hold in ((0.02, 0.04, 24), (0.02, 0.03, 24), (0.02, 0.05, 24), (0.015, 0.04, 24), (0.025, 0.04, 24),
                         (0.03, 0.04, 36), (0.02, 0.04, 12), (0.02, 0.04, 36)):
        r = Rule(6, 0.04, tg, st, hold)
        for mk in mks:
            out.append(stats_row(f"+{tg:.1%} / -{st:.0%} / {hold}h".replace(".0%", "%"), mk, trades(mk, r)))
    out.append("")

    sizers = [("40% of the balance (today)", fixed(0.4)), ("60% of the balance", fixed(0.6)),
              ("80% of the balance", fixed(0.8)), ("100% of the balance", fixed(1.0)),
              ("risk 25% of the room above $950", cushion(0.25)), ("risk 35% of the room above $950", cushion(0.35)),
              ("risk 50% of the room above $950", cushion(0.50))]
    for title, r in (("3. Position size: today's rule (fall 5% in 4h)", current),
                     ("4. Position size: the proposed rule (fall 4% in 6h)", proposed)):
        out += [f"## {title}", "", "Share of the weekly challenge runs that passed, failed or were still open after a year.", ""]
        out += RUNS_HEAD
        for name, size_of in sizers:
            for mk in mks:
                out.append(f"| {name} | ${size_of(START, r.stop):,.0f} | {mk.symbol} | "
                           f"{challenge(mk, trades(mk, r), size_of, r.stop).cell()} |")
        out.append("")

    out += ["## 5. What weakens it", "",
            "The proposed rule, risking 35% of the room above $950, when reality is less kind than the model.", ""]
    out += ["| Case | Pair | Avg per trade | Passed | Failed | Still open | Passed within 90 days | Median days to pass |",
            "|---|---|---|---|---|---|---|---|"]
    cases = [("as modelled", proposed, 1.0), ("buy 30 to 45 minutes after the signal", Rule(6, 0.04, delay=2), 1.0),
             ("exit slippage 0.5%", Rule(6, 0.04, slip=0.005), 1.0), ("half the signals missed", proposed, 0.5)]
    for name, r, catch in cases:
        for mk in mks:
            tr = trades(mk, r)
            if catch < 1:
                rng = random.Random(7)
                tr = [t for t in tr if rng.random() < catch]
            out.append(f"| {name} | {mk.symbol} | {mean(t.net for t in tr):+.2%} | "
                       f"{challenge(mk, tr, cushion(0.35), r.stop, r.slip).cell()} |")
    out.append("")

    out += ["## 6. For comparison: one big swing", "",
            "No signal: buy BTC on any day (tried twice a week through the history), sell when equity reaches $1,120, "
            "or sell when it falls to the level given.", "",
            "| Position | Pair | Passed | Median days to pass | Stopped out | Touched $950 |", "|---|---|---|---|---|---|"]
    for share, stop_eq in ((1.0, 1000.0), (1.0, 985.0), (1.0, 970.0), (0.6, 985.0)):
        for mk in mks:
            out.append(swing(mk, share, stop_eq))
    out.append("")

    out += ["## 7. Nights", ""]
    for mk in mks:
        n, worst, over5 = worst_nights(mk)
        out.append(f"- {mk.symbol}: {n} nights; the worst fall between 22:30 and 06:30 was {worst:.1%}; "
                   f"{over5} nights fell more than 5%.")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data/history"))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    text = report(args.root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
