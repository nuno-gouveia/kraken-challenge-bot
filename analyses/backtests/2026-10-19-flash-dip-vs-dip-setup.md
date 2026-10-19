# Backtest: flash dip vs dip setup (BTCEUR, 01 Oct 2023 to 18 Oct 2026)

Costs per round trip: fee 0.40% each side plus 0.3% exit slippage (1.1%). Sizing: 2% of balance at risk, at most 40% of balance per position. Challenge start $1,050, pass $1,120, fail $950. Returns per trade are after costs. Source: Binance archive (research only).

## Flash dip: best 10 of 240 variants (all hours)

| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |
|---|---|---|---|---|---|---|---|---|
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 19 | 100% | +0.40% | +0.40% | $1,082 | 0.0% | never | never |
| fall 6% in 1h, target +3.0%, stop -2%, max 24h | 10 | 60% | +0.48% | -3.10% | $1,070 | 1.7% | never | never |
| fall 6% in 1h, target +1.5%, stop -4%, max 24h | 10 | 100% | +0.40% | +0.40% | $1,067 | 0.0% | never | never |
| fall 5% in 1h, target +1.5%, stop -3%, max 24h | 19 | 95% | +0.16% | -4.10% | $1,063 | 1.6% | never | never |
| fall 6% in 1h, target +3.0%, stop -3%, max 24h | 10 | 60% | +0.28% | -4.10% | $1,061 | 2.5% | never | never |
| fall 6% in 2h, target +3.0%, stop -2%, max 24h | 11 | 55% | +0.15% | -3.10% | $1,057 | 2.9% | never | never |
| fall 6% in 1h, target +2.0%, stop -2%, max 24h | 10 | 80% | +0.10% | -3.10% | $1,054 | 2.1% | never | never |
| fall 6% in 1h, target +1.5%, stop -2%, max 24h | 10 | 90% | +0.05% | -3.10% | $1,052 | 1.2% | never | never |
| fall 6% in 3h, target +1.5%, stop -2%, max 24h | 18 | 89% | +0.01% | -3.10% | $1,051 | 1.4% | never | never |
| fall 6% in 2h, target +1.5%, stop -4%, max 24h | 13 | 92% | -0.02% | -5.10% | $1,049 | 2.0% | never | never |

Best by year: 2023: 2 trades, +0.40% avg, 2024: 9 trades, +0.40% avg, 2025: 5 trades, +0.40% avg, 2026: 3 trades, +0.40% avg.

## Flash dip: best 10 of 240 variants (signals in quiet hours skipped)

| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |
|---|---|---|---|---|---|---|---|---|
| fall 5% in 1h, target +1.5%, stop -4%, max 24h, awake hours only | 13 | 100% | +0.40% | +0.40% | $1,072 | 0.0% | never | never |
| fall 6% in 3h, target +2.0%, stop -3%, max 24h, awake hours only | 10 | 90% | +0.40% | -4.10% | $1,067 | 1.6% | never | never |
| fall 6% in 3h, target +1.5%, stop -2%, max 24h, awake hours only | 10 | 100% | +0.40% | +0.40% | $1,067 | 0.0% | never | never |
| fall 6% in 3h, target +1.5%, stop -3%, max 24h, awake hours only | 10 | 100% | +0.40% | +0.40% | $1,067 | 0.0% | never | never |
| fall 6% in 3h, target +1.5%, stop -4%, max 24h, awake hours only | 10 | 100% | +0.40% | +0.40% | $1,067 | 0.0% | never | never |
| fall 6% in 3h, target +2.0%, stop -4%, max 24h, awake hours only | 10 | 90% | +0.30% | -5.10% | $1,062 | 2.0% | never | never |
| fall 6% in 3h, target +3.0%, stop -3%, max 24h, awake hours only | 10 | 60% | +0.28% | -4.10% | $1,061 | 2.5% | never | never |
| fall 5% in 1h, target +3.0%, stop -4%, max 24h, awake hours only | 13 | 54% | +0.15% | -5.10% | $1,058 | 4.2% | never | never |
| fall 6% in 3h, target +2.0%, stop -2%, max 24h, awake hours only | 10 | 80% | +0.10% | -3.10% | $1,054 | 1.2% | never | never |
| fall 6% in 3h, target +3.0%, stop -4%, max 24h, awake hours only | 10 | 60% | +0.08% | -5.10% | $1,053 | 3.3% | never | never |

Best by year: 2023: 1 trades, +0.40% avg, 2024: 7 trades, +0.40% avg, 2025: 3 trades, +0.40% avg, 2026: 2 trades, +0.40% avg.

## How fast you buy, and what it costs, decide the result

Balance after three years for the leading rules, by round-trip cost and by how long after the signal the buy happens.

| Rule | Cost | Buy after 15 min | 30 min | 60 min |
|---|---|---|---|---|
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 1.10% | $1,082 (19 trades, 100% won) | $1,013 (19 trades, 84% won) | $975 (18 trades, 72% won) |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 0.62% | $1,122 (19 trades, 100% won) | $1,050 (19 trades, 84% won) | $1,010 (18 trades, 72% won) |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 0.20% | $1,159 (19 trades, 100% won) | $1,084 (19 trades, 84% won) | $1,041 (18 trades, 72% won) |
| fall 5% in 3h, target +1.5%, stop -4%, max 24h | 1.10% | $998 (39 trades, 85% won) | $954 (37 trades, 81% won) | $928 (36 trades, 75% won) |
| fall 5% in 3h, target +1.5%, stop -4%, max 24h | 0.62% | $1,075 (39 trades, 87% won) | $1,024 (37 trades, 81% won) | $994 (36 trades, 75% won) |
| fall 5% in 3h, target +1.5%, stop -4%, max 24h | 0.20% | $1,148 (39 trades, 87% won) | $1,090 (37 trades, 81% won) | $1,057 (36 trades, 75% won) |
| fall 6% in 1h, target +3.0%, stop -2%, max 24h | 1.10% | $1,070 (10 trades, 60% won) | $1,059 (10 trades, 70% won) | $1,049 (10 trades, 60% won) |
| fall 6% in 1h, target +3.0%, stop -2%, max 24h | 0.62% | $1,091 (10 trades, 80% won) | $1,079 (10 trades, 70% won) | $1,070 (10 trades, 60% won) |
| fall 6% in 1h, target +3.0%, stop -2%, max 24h | 0.20% | $1,109 (10 trades, 80% won) | $1,097 (10 trades, 70% won) | $1,088 (10 trades, 70% won) |

Before costs: how often a buy after the fall reached +1.5% before falling another 4% (15 min delay).

| Fall | Within | Events | Bounced +1.5% first | Stopped | Neither in 24h |
|---|---|---|---|---|---|
| 3% | 1h | 76 | 53 | 13 | 10 |
| 3% | 3h | 170 | 106 | 34 | 30 |
| 3% | 6h | 226 | 133 | 33 | 60 |
| 4% | 1h | 28 | 22 | 5 | 1 |
| 4% | 3h | 77 | 57 | 14 | 6 |
| 4% | 6h | 113 | 84 | 17 | 12 |
| 5% | 1h | 19 | 19 | 0 | 0 |
| 5% | 3h | 39 | 33 | 5 | 1 |
| 5% | 6h | 61 | 46 | 13 | 2 |
| 6% | 1h | 10 | 10 | 0 | 0 |
| 6% | 3h | 18 | 16 | 2 | 0 |
| 6% | 6h | 40 | 32 | 7 | 1 |

## Current rules: dip setup (three readings of 'oversold') and Plan B breakout

| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |
|---|---|---|---|---|---|---|---|---|
| dip setup: fall 1.5 ATR in 2 days, RSI below 30, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 7 | 29% | -4.06% | -8.98% | $946 | 9.9% | never | 23 Feb 2026 |
| dip setup: fall 1.5 ATR in 2 days, RSI below 45, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 16 | 44% | -1.74% | -8.98% | $946 | 14.4% | never | 18 Nov 2025 |
| dip setup: fall 1.5 ATR in 2 days, RSI below 60, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 24 | 25% | -3.16% | -8.98% | $786 | 25.7% | never | 04 Sep 2024 |
| Plan B breakout: close above 20-day high, stop 1.2 ATR, T1 1.2, T2 2.4 ATR | 39 | 51% | -0.85% | -6.96% | $919 | 14.9% | never | 24 Jul 2026 |

- dip setup: fall 1.5 ATR in 2 days, RSI below 30, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2024: 3 trades, -2.79% avg, 2025: 3 trades, -3.69% avg, 2026: 1 trades, -8.98% avg.
- dip setup: fall 1.5 ATR in 2 days, RSI below 45, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2024: 6 trades, +0.11% avg, 2025: 8 trades, -3.22% avg, 2026: 2 trades, -1.34% avg.
- dip setup: fall 1.5 ATR in 2 days, RSI below 60, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2023: 1 trades, -5.25% avg, 2024: 9 trades, -2.06% avg, 2025: 11 trades, -4.10% avg, 2026: 3 trades, -2.32% avg.
- Plan B breakout: close above 20-day high, stop 1.2 ATR, T1 1.2, T2 2.4 ATR: 2023: 4 trades, -0.18% avg, 2024: 16 trades, -0.38% avg, 2025: 7 trades, +1.93% avg, 2026: 12 trades, -3.31% avg.
