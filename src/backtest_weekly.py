"""Backtest: should the flash dip only buy after a down week? Research only.

    python -m src.backtest_weekly [--out analyses/backtests/NAME.md]

Nuno, 21 Nov 2026, after two losing flash-dip trades in a row. A first look
at the history suggested the rule's losers come from dips in a calm or rising
week, and its best trades from dips after a bad week. That pattern was found
by looking at the same data, so this file tests it as strictly as the data
allows:

1. Is it the 7-day window and the 5% line, or does any nearby window and line
   say the same? (A real effect should not depend on one exact setting.)
2. Does it hold in each half of the history, and in each year, separately?
3. Could a random filter that skips as many trades do as well? (Permutation
   test: how often does dropping the same number of trades at random give an
   average as good?)
4. Does it hold on ETH, LINK, BCH, DOGE and SHIB, which were never looked at
   for this question?
5. Does it pass the challenge more often, given it trades less?

Same engine and strictness as src/backtest_active.py: 15-minute candles, quiet
hours, exits due at night taken at the 06:30 price, the $950 floor touched
inside a trade. The filter is read on the signal candle, so it uses only what
the bot would know then; a skipped signal does not block the next one.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from src.backtest_active import (BARS_H, SYMBOLS, YEAR_S, Market, Rule, Trade, challenge, cushion, market,
                                 one_trade)
from src.backtest_assets import RATIO

OTHERS = ("ETHUSDT", "LINKUSDT", "BCHUSDT", "DOGEUSDT", "SHIBUSDT")
RULE = Rule()   # today's rule: fall 4% in 6h, +2% / -4% / 24h


def change(mk: Market, i: int, days: int) -> float | None:
    """Close of candle i against the close `days` days earlier."""
    p = i - days * 24 * BARS_H
    return mk.bars[i].c / mk.bars[p].c - 1 if p >= 0 else None


def filtered(mk: Market, r: Rule, days: int | None, line: float | None) -> list[Trade]:
    """The rule's trades, buying only when the `days`-day change at the signal is at or under `line`.
    The first `days` of history are skipped for every setting, so all rows cover the same period."""
    warm = 14 * 24 * BARS_H
    out, free_from = [], 0
    for i in mk.dips(r.hours, r.drop):
        k = i + r.delay
        if i < max(free_from, warm) or k >= len(mk.bars) - 2 or mk.asleep[k]:
            continue
        if days is not None and change(mk, i, days) > line:
            continue
        t = one_trade(mk, k, r.target, r.stop, r.hold_h * BARS_H, r.slip)
        out.append(t)
        free_from = t.m + r.hours * BARS_H
    return out


def years(mk: Market) -> float:
    return (mk.bars[-1].t - mk.bars[0].t - 14 * 86400) / YEAR_S


def yr(mk: Market, t: Trade) -> int:
    return datetime.fromtimestamp(mk.bars[t.k].t, timezone.utc).year


def avg(tr: list[Trade]) -> str:
    return f"{mean(t.net for t in tr):+.2%}" if tr else "n/a"


def row(label: str, mk: Market, tr: list[Trade]) -> str:
    if not tr:
        return f"| {label} | {mk.symbol} | 0 | | | | |"
    by_year = " / ".join(avg([t for t in tr if yr(mk, t) == y]) for y in (2023, 2024, 2025, 2026))
    stops = sum(t.why.startswith("stop") for t in tr)
    return (f"| {label} | {mk.symbol} | {len(tr) / years(mk):.0f} | {sum(t.net > 0 for t in tr) / len(tr):.0%} | "
            f"{avg(tr)} | {by_year} | {stops} |")


HEAD = ["| Filter | Pair | Trades a year | Win | Avg per trade | Avg 2023 / 2024 / 2025 / 2026 | Stopped |",
        "|---|---|---|---|---|---|---|"]


def label(days: int | None, line: float | None) -> str:
    if days is None:
        return "none (today)"
    return f"{days}d change at or under {line:+.1%}".replace(".0%", "%")


def permutation(mk: Market, base: list[Trade], kept: list[Trade], n: int = 20000) -> float:
    """Share of random subsets, as large as `kept`, whose average is at least as good as `kept`'s."""
    rng, nets, goal = random.Random(21), [t.net for t in base], mean(t.net for t in kept)
    hits = sum(mean(rng.sample(nets, len(kept))) >= goal for _ in range(n))
    return hits / n


def report(root: Path) -> str:
    mks = {s: market(root, s) for s in SYMBOLS}
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%d %b %Y")
    first = next(iter(mks.values()))
    out = [f"# Backtest: buy the flash dip only after a down week ({day(first.bars[0].t)} to {day(first.bars[-1].t)})", "",
           "Today's rule (fall 4% in 6h, sell at +2%, -4% or after 24h), with one extra condition: buy only when BTC's "
           "change over the past N days, read on the signal candle, is at or under a line. 15-minute candles (Binance "
           "archive), exit slippage 0.3%, quiet hours modelled, the $950 floor checked inside each trade. The first 14 "
           "days of history are skipped by every row so all rows cover the same period. Research only.", ""]

    # 1. the grid
    out += ["## 1. Every nearby window and line", "",
            "If the effect is real, nearby settings should agree, not only 7 days and -5%.", ""] + HEAD
    grid = [(None, None)] + [(d, l) for d in (3, 7, 14) for l in (0.0, -0.03, -0.05, -0.075, -0.10)]
    for d, l in grid:
        for mk in mks.values():
            out.append(row(label(d, l), mk, filtered(mk, RULE, d, l)))
    out.append("")

    # 1b. the complement: the trades the filter would skip
    out += ["## 2. The trades the 7d / -5% filter would skip", "",
            "The other side of the same split: dips that came in a week down less than 5%, or up.", "",
            "| Trades | Pair | Count | Win | Avg per trade | Stopped |", "|---|---|---|---|---|---|"]
    for mk in mks.values():
        base, kept = filtered(mk, RULE, None, None), filtered(mk, RULE, 7, -0.05)
        ks = {t.k for t in kept}
        skip = [t for t in base if t.k not in ks]
        for name, tr in (("kept", kept), ("skipped", skip)):
            out.append(f"| {name} | {mk.symbol} | {len(tr)} | {sum(t.net > 0 for t in tr) / len(tr):.0%} | {avg(tr)} | "
                       f"{sum(t.why.startswith('stop') for t in tr)} |")
    out.append("")

    # 3. halves
    out += ["## 3. Each half of the history on its own", "",
            "| Filter | Pair | Half | Trades | Win | Avg per trade |", "|---|---|---|---|---|---|"]
    for mk in mks.values():
        mid = (mk.bars[0].t + mk.bars[-1].t) / 2
        for d, l in ((None, None), (7, -0.05)):
            tr = filtered(mk, RULE, d, l)
            for half, part in (("first", [t for t in tr if mk.bars[t.k].t < mid]),
                               ("second", [t for t in tr if mk.bars[t.k].t >= mid])):
                out.append(f"| {label(d, l)} | {mk.symbol} | {half} | {len(part)} | "
                           f"{sum(t.net > 0 for t in part) / len(part):.0%} | {avg(part)} |")
    out.append("")

    # 4. permutation
    out += ["## 4. Could a random filter do as well?", "",
            "Drop as many trades as the filter does, at random, 20,000 times. The share of those random picks whose "
            "average is at least as good as the filter's. Under 5% suggests the filter picks better than luck; around "
            "50% means it does not.", "",
            "| Filter | Pair | Kept | Avg kept | Avg of all | Random picks as good |", "|---|---|---|---|---|---|"]
    for mk in mks.values():
        base = filtered(mk, RULE, None, None)
        for d, l in ((7, -0.05), (7, -0.03), (14, -0.05), (3, -0.03)):
            kept = filtered(mk, RULE, d, l)
            ks = {t.k for t in kept}
            pool = [t for t in base if t.k in ks]   # same trades, compared against the unfiltered set
            out.append(f"| {label(d, l)} | {mk.symbol} | {len(kept)} | {avg(kept)} | {avg(base)} | "
                       f"{permutation(mk, base, pool):.1%} |")
    out.append("")

    # 5. other assets
    out += ["## 5. The other five assets (never looked at for this question)", "",
            "The rule scaled to each asset's volatility as in `src/backtest_assets.py`; the filter is the same "
            "7-day / -5% line on that asset's own price.", "",
            "| Asset | Filter | Trades a year | Win | Avg per trade | Random picks as good |", "|---|---|---|---|---|---|"]
    for s in OTHERS:
        try:
            mk = market(root, s)
        except (FileNotFoundError, ValueError):
            out.append(f"| {s[:-4]} | no data | | | | |")
            continue
        k = RATIO[s]
        r = Rule(6, 0.04 * k, 0.02 * k, 0.04 * k)
        base, kept = filtered(mk, r, None, None), filtered(mk, r, 7, -0.05)
        ks = {t.k for t in kept}
        pool = [t for t in base if t.k in ks]
        for name, tr, p in (("none", base, ""), ("7d at or under -5%", kept,
                                                  f"{permutation(mk, base, pool):.1%}" if pool else "")):
            win = f"{sum(t.net > 0 for t in tr) / len(tr):.0%}" if tr else ""
            out.append(f"| {s[:-4]} | {name} | {len(tr) / years(mk):.0f} | {win} | {avg(tr)} | {p} |")
    out.append("")

    # 6. the challenge
    out += ["## 6. The challenge: does trading less but better pass more often?", "",
            "Sized to risk 35% of the room above $950, from $1,050.60. One run starts every week with a year of "
            "history ahead; the runs overlap, so read these as a description of the past, not as odds.", "",
            "| Filter | Pair | Passed | Failed | Still open | Passed within 90 days | Median days to pass |",
            "|---|---|---|---|---|---|---|"]
    for d, l in ((None, None), (7, 0.0), (7, -0.03), (7, -0.05), (7, -0.075), (14, -0.05)):
        for mk in mks.values():
            out.append(f"| {label(d, l)} | {mk.symbol} | "
                       f"{challenge(mk, filtered(mk, RULE, d, l), cushion(0.35), RULE.stop).cell()} |")
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
