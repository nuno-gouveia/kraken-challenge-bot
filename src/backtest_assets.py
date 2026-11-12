"""Backtest: do the challenge's other five assets add trades with an edge? Research only.

    python -m src.backtest_assets [--out analyses/backtests/NAME.md]

Nuno, 12 Nov 2026: the BTC flash dip gives 2 to 3 signals a month; can ETH,
LINK, BCH, DOGE and SHIB add more? Same engine and the same strictness as
src/backtest_active.py (quiet hours, exits due at night taken at the 06:30
price, the floor inside a trade), on 15-minute candles against USDT.

It asks:

1. Does the BTC rule, scaled to each asset's volatility, work on that asset?
2. When BTC gives its signal, is buying another asset better than buying BTC?
3. Do only the extreme falls bounce (as in BTC, the sharper the better)?
4. Would such a rule, added to the BTC rule, pass the challenge more often?
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from src.backtest_active import (BARS_H, FLOOR, SLIP, START, TARGET, YEAR_S, Market, Rule, cushion, market,
                                 one_trade, trades)

BTC = "BTCUSDT"
OTHERS = ("ETHUSDT", "LINKUSDT", "BCHUSDT", "DOGEUSDT", "SHIBUSDT")
VOLATILE = ("LINKUSDT", "BCHUSDT", "DOGEUSDT", "SHIBUSDT")
# How much more each asset moves than BTC (median 6-hour range, section 1), rounded.
RATIO = {"BTCUSDT": 1.0, "ETHUSDT": 1.45, "LINKUSDT": 1.9, "BCHUSDT": 1.75, "DOGEUSDT": 1.9, "SHIBUSDT": 1.9}
CRASH = (1760054400, 1760227200)   # 10 and 11 Oct 2025 UTC: the liquidation cascade


@dataclass
class Ev:
    """One trade on any asset, in clock time, so trades on different assets can be put in one queue."""
    t_in: int
    t_out: int
    net: float
    mae: float
    mfe: float
    stop: float
    asset: str


def events(mk: Market, r: Rule, at: list[int] | None = None) -> list[Ev]:
    """The rule's trades on this market; with `at`, buy at those candles instead (another asset's signal)."""
    if at is None:
        tr = trades(mk, r)
    else:
        tr, free_from = [], 0
        for i in at:
            k = i + r.delay
            if i < free_from or k >= len(mk.bars) - 2 or mk.asleep[i] or mk.asleep[k]:
                continue
            t = one_trade(mk, k, r.target, r.stop, r.hold_h * BARS_H, r.slip)
            tr.append(t)
            free_from = t.m + r.hours * BARS_H
    return [Ev(mk.bars[t.k].t, mk.bars[t.m].t, t.net, t.mae, t.mfe, r.stop, mk.symbol) for t in tr]


def one_at_a_time(evs: list[Ev]) -> list[Ev]:
    out, free = [], 0
    for e in sorted(evs, key=lambda e: e.t_in):
        if e.t_in >= free:
            out.append(e)
            free = e.t_out
    return out


def year(e: Ev) -> int:
    return datetime.fromtimestamp(e.t_in, timezone.utc).year


def row(label: str, evs: list[Ev], years: float, slip: float = SLIP) -> str:
    if len(evs) < 6:
        return f"| {label} | {len(evs) / years:.0f} | too few | | | | | |"
    by = " / ".join(f"{mean(x):+.2f}% ({len(x)})" if (x := [e.net * 100 for e in evs if year(e) == y]) else "none"
                    for y in (2024, 2025, 2026))
    risk_units = sum(e.net / (e.stop + slip) for e in evs) / years   # profit a year, in units of the planned risk
    return (f"| {label} | {len(evs) / years:.0f} | {sum(e.net > 0 for e in evs) / len(evs):.0%} | "
            f"{mean(e.net for e in evs):+.2%} | {risk_units:+.1f} | {by} | {min(e.net for e in evs):+.0%} | "
            f"{min(e.mae for e in evs):+.0%} |")


HEAD = ["| Rule | Trades a year | Win | Avg per trade | Profit a year, in risks | Avg 2024 / 2025 / 2026 (trades) | Worst trade | Worst dip while held |",
        "|---|---|---|---|---|---|---|---|"]


def challenge(evs: list[Ev], t0: int, t1: int, share: float = 0.35) -> str:
    size_of = cushion(share)
    entries = [e.t_in for e in evs]
    passed, failed, n, s = [], 0, 0, t0
    while s < t1 - YEAR_S:
        n += 1
        bal, j = START, bisect_left(entries, s)
        while j < len(evs) and entries[j] < s + YEAR_S:
            e = evs[j]
            j += 1
            size = size_of(bal, e.stop)
            if bal + size * e.mae <= FLOOR:
                failed += 1
                break
            if bal + size * (e.mfe - SLIP) >= TARGET or bal + size * e.net >= TARGET:
                passed.append((e.t_out - s) / 86400)
                break
            bal += size * e.net
            if bal <= FLOOR:
                failed += 1
                break
        s += 7 * 86400
    p = len(passed) / n
    days = f"{median(passed):.0f}" if passed else "n/a"
    return (f"{p:.0%} | {failed / n:.0%} | {1 - p - failed / n:.0%} | "
            f"{sum(d <= 90 for d in passed) / n:.0%} | {days}")


def six_hour_range(mk: Market) -> float:
    w = 6 * BARS_H
    return median(max(b.h for b in mk.bars[i:i + w]) / min(b.l for b in mk.bars[i:i + w]) - 1
                  for i in range(0, len(mk.bars) - w, w))


def worst_night(mk: Market) -> float:
    worst, i = 0.0, 1
    while i < len(mk.bars):
        if mk.asleep[i] and not mk.asleep[i - 1]:
            ref, low = mk.bars[i - 1].c, mk.bars[i - 1].c
            while i < len(mk.bars) and mk.asleep[i]:
                low = min(low, mk.bars[i].l)
                i += 1
            worst = min(worst, low / ref - 1)
        else:
            i += 1
    return worst


def report(root: Path) -> str:
    mks = {s: market(root, s) for s in (BTC,) + OTHERS}
    t0 = max(m.bars[0].t for m in mks.values())
    for m in mks.values():   # one common period
        cut = next(i for i, b in enumerate(m.bars) if b.t >= t0)
        m.bars, m.asleep = m.bars[cut:], m.asleep[cut:]
    t1 = min(m.bars[-1].t for m in mks.values())
    years = (t1 - t0) / YEAR_S
    day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%d %b %Y")
    btc = mks[BTC]
    pct = lambda x: f"{x:.1%}".replace(".0%", "%")

    out = [f"# Backtest: the other five assets ({day(t0)} to {day(t1)})", "",
           "ETH, LINK, BCH, DOGE and SHIB against USDT, 15-minute candles (Binance archive, research only), with BTC "
           f"for comparison. Exit slippage {SLIP:.1%} unless stated, no fees. Quiet hours 22:30 to 06:30 Lisbon are "
           "modelled as in `2026-11-12-more-active.md`. \"Profit a year, in risks\" adds up each trade's result "
           "divided by what it would lose at its stop: it compares rules whose stops differ. Many rules were tried "
           "here, so a single good row proves little; look for rows that agree.", "",
           "## 1. How much more they move than BTC", "",
           "| Asset | Typical 6-hour range | Against BTC | Worst night (22:30 to 06:30) |", "|---|---|---|---|"]
    base = six_hour_range(btc)
    for s, m in mks.items():
        r = six_hour_range(m)
        out.append(f"| {s[:-4]} | {r:.1%} | {r / base:.2f}x | {worst_night(m):.0%} |")
    out += ["", "The worst nights are 10 Oct 2025, when a liquidation cascade took these coins down 25% to 55% within "
            "minutes on Binance. Kraken's prices that night were less extreme, but a position in one of them would "
            "have ended the challenge at almost any size.", ""]

    out += ["## 2. The BTC rule on each asset, scaled to its volatility", "",
            "BTC's rule is: fall 4% in 6 hours, sell at +2%, at -4% or after 24 hours. Each asset gets the same rule "
            "with every number multiplied by how much more it moves.", ""] + HEAD
    for s, m in mks.items():
        k = RATIO[s]
        r = Rule(6, 0.04 * k, 0.02 * k, 0.04 * k)
        out.append(row(f"{s[:-4]}: fall {pct(r.drop)} in 6h, +{pct(r.target)} / -{pct(r.stop)}", events(m, r), years))
    out.append("")

    out += ["## 3. On BTC's signal, buy another asset instead", "",
            "Same moments as the BTC rule (BTC 4% under its 6-hour high), exits scaled to the asset bought.", ""] + HEAD
    by_time = {s: {b.t: i for i, b in enumerate(m.bars)} for s, m in mks.items()}
    signal_times = [btc.bars[i].t for i in btc.dips(6, 0.04)]
    for s, m in mks.items():
        k = RATIO[s]
        at = [by_time[s][t] for t in signal_times if t in by_time[s]]
        r = Rule(6, 0.04, 0.02 * k, 0.04 * k)
        out.append(row(f"buy {s[:-4]}, +{pct(r.target)} / -{pct(r.stop)}", events(m, r, at), years))
    out.append("")

    out += ["## 4. Only the extreme falls", "",
            "LINK, BCH, DOGE and SHIB together, one position at a time: the asset falls X in W hours, sell at +X/2, "
            "at -X or after 24 hours.", ""] + HEAD

    def pooled(hours: int, x: float, slip: float = SLIP, skip_crash: bool = False) -> list[Ev]:
        evs = [e for s in VOLATILE for e in events(mks[s], Rule(hours, x, x / 2, x, slip=slip))]
        if skip_crash:
            evs = [e for e in evs if not CRASH[0] <= e.t_in < CRASH[1]]
        return one_at_a_time(evs)

    for hours in (2, 4, 6):
        for x in (0.06, 0.08, 0.09, 0.10, 0.12):
            out.append(row(f"fall {pct(x)} in {hours}h", pooled(hours, x), years))
    out.append("")
    out += ["The same at the two thresholds that look best, under harder assumptions:", ""] + HEAD
    for x in (0.09, 0.10):
        out.append(row(f"fall {pct(x)} in 4h, slippage 0.6%", pooled(4, x, slip=0.006), years, 0.006))
        out.append(row(f"fall {pct(x)} in 4h, without 10 and 11 Oct 2025", pooled(4, x, skip_crash=True), years))
    out.append("")
    flush = pooled(4, 0.10)
    counts = ", ".join(f"{s[:-4]} {sum(e.asset == s for e in flush)}" for s in VOLATILE)
    out += [f"Fall 10% in 4h, trades by asset over the whole period: {counts}.", ""]

    out += ["## 5. Added to the BTC rule: challenge runs", "",
            "Weekly challenge starts from $1,050.60, one year each, 35% of the room above $950 at risk on each "
            "trade's own stop, one position at a time across all assets.", "",
            "| Rules | Trades a year | Passed | Failed | Still open | Passed within 90 days | Median days to pass |",
            "|---|---|---|---|---|---|---|"]
    btc_evs = events(btc, Rule(6, 0.04))
    for name, evs in (("BTC rule alone", btc_evs),
                      ("BTC rule + fall 10% in 4h on LINK, BCH, DOGE, SHIB", one_at_a_time(btc_evs + flush)),
                      ("BTC rule + fall 9% in 4h on LINK, BCH, DOGE, SHIB", one_at_a_time(btc_evs + pooled(4, 0.09))),
                      ("the same, 10% in 4h, without 10 and 11 Oct 2025",
                       one_at_a_time(btc_evs + pooled(4, 0.10, skip_crash=True)))):
        out.append(f"| {name} | {len(evs) / years:.0f} | {challenge(evs, t0, t1)} |")
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
