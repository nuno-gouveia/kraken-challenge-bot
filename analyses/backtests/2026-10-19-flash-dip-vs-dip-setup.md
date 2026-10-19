# Backtest: flash dip vs dip setup (BTCEUR, 01 Oct 2023 to 18 Oct 2026)

Costs per round trip: fee 0.00% each side plus 0.3% exit slippage (0.3%). Sizing: 2% of balance at risk, at most 40% of balance per position. Challenge start $1,050, pass $1,120, fail $950. Returns per trade are after costs. Source: Binance archive (research only).

## Flash dip: best 10 of 240 variants (all hours)

| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |
|---|---|---|---|---|---|---|---|---|
| fall 4% in 6h, target +3.0%, stop -4%, max 24h | 106 | 66% | +0.45% | -4.30% | $1,262 | 5.9% | 09 Jul 2024 | never |
| fall 4% in 6h, target +2.0%, stop -4%, max 24h | 111 | 73% | +0.27% | -4.30% | $1,178 | 6.5% | 25 Feb 2025 | never |
| fall 5% in 4h, target +2.0%, stop -3%, max 24h | 49 | 76% | +0.52% | -3.30% | $1,160 | 3.9% | 19 Dec 2024 | never |
| fall 5% in 4h, target +2.0%, stop -4%, max 24h | 49 | 80% | +0.52% | -4.30% | $1,159 | 4.1% | 19 Dec 2024 | never |
| fall 5% in 4h, target +3.0%, stop -3%, max 24h | 46 | 67% | +0.54% | -3.30% | $1,158 | 3.9% | 04 Aug 2024 | never |
| fall 5% in 4h, target +3.0%, stop -4%, max 24h | 46 | 72% | +0.50% | -4.30% | $1,147 | 3.5% | 06 Dec 2024 | never |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 19 | 100% | +1.20% | +1.20% | $1,150 | 0.0% | 07 Mar 2025 | never |
| fall 5% in 4h, target +1.5%, stop -4%, max 24h | 50 | 86% | +0.42% | -4.30% | $1,140 | 4.4% | 07 Feb 2026 | never |
| fall 4% in 6h, target +3.0%, stop -3%, max 24h | 107 | 60% | +0.19% | -3.30% | $1,131 | 6.5% | 16 Aug 2024 | never |
| fall 4% in 4h, target +3.0%, stop -4%, max 24h | 87 | 63% | +0.23% | -4.30% | $1,131 | 8.8% | 06 Dec 2024 | never |

Best by year: 2023: 5 trades, +0.87% avg, 2024: 48 trades, +0.51% avg, 2025: 38 trades, +0.68% avg, 2026: 15 trades, -0.47% avg.

## Flash dip: best 10 of 240 variants (signals in quiet hours skipped)

| Rule | Trades | Win | Avg/trade | Worst | Balance after | Max drawdown | Pass ($1,120) | Fail ($950) |
|---|---|---|---|---|---|---|---|---|
| fall 4% in 6h, target +3.0%, stop -4%, max 24h, awake hours only | 87 | 64% | +0.30% | -4.30% | $1,160 | 5.5% | 11 Nov 2024 | never |
| fall 5% in 4h, target +3.0%, stop -3%, max 24h, awake hours only | 30 | 70% | +0.68% | -3.30% | $1,137 | 3.1% | 05 Aug 2024 | never |
| fall 4% in 6h, target +3.0%, stop -2%, max 24h, awake hours only | 92 | 51% | +0.20% | -2.30% | $1,127 | 8.2% | 05 Jul 2024 | never |
| fall 5% in 4h, target +2.0%, stop -3%, max 24h, awake hours only | 31 | 77% | +0.57% | -3.30% | $1,126 | 2.6% | 03 Feb 2026 | never |
| fall 4% in 6h, target +3.0%, stop -3%, max 24h, awake hours only | 88 | 60% | +0.20% | -3.30% | $1,120 | 8.0% | 16 Aug 2024 | never |
| fall 5% in 4h, target +3.0%, stop -4%, max 24h, awake hours only | 30 | 73% | +0.58% | -4.30% | $1,123 | 4.0% | 05 Aug 2024 | never |
| fall 5% in 4h, target +1.5%, stop -3%, max 24h, awake hours only | 33 | 85% | +0.52% | -3.30% | $1,123 | 2.2% | 25 Jun 2026 | never |
| fall 5% in 4h, target +1.5%, stop -4%, max 24h, awake hours only | 33 | 88% | +0.52% | -4.30% | $1,123 | 2.9% | 25 Jun 2026 | never |
| fall 5% in 3h, target +3.0%, stop -3%, max 24h, awake hours only | 24 | 71% | +0.68% | -3.30% | $1,119 | 2.7% | 05 Aug 2024 | never |
| fall 5% in 4h, target +2.0%, stop -4%, max 24h, awake hours only | 31 | 81% | +0.50% | -4.30% | $1,116 | 3.4% | 21 Jan 2025 | never |

Best by year: 2023: 5 trades, +0.87% avg, 2024: 42 trades, +0.38% avg, 2025: 29 trades, +0.35% avg, 2026: 11 trades, -0.37% avg.

## How fast you buy, and slippage, decide the result

Balance after three years for the leading rules, by round-trip cost and by how long after the signal the buy happens.

| Rule | Cost | Buy after 15 min | 30 min | 60 min |
|---|---|---|---|---|
| fall 5% in 4h, target +2.0%, stop -4%, max 24h | 0.30% | $1,159 (49 trades, 80% won) | $1,045 (46 trades, 70% won) | $1,084 (46 trades, 74% won) |
| fall 5% in 4h, target +2.0%, stop -4%, max 24h | 0.50% | $1,115 (49 trades, 80% won) | $1,007 (46 trades, 70% won) | $1,045 (46 trades, 72% won) |
| fall 5% in 4h, target +2.0%, stop -4%, max 24h | 1.10% | $991 (49 trades, 78% won) | $902 (46 trades, 67% won) | $935 (46 trades, 72% won) |
| fall 5% in 4h, target +1.5%, stop -3%, max 24h | 0.30% | $1,134 (50 trades, 82% won) | $1,045 (48 trades, 73% won) | $1,021 (47 trades, 70% won) |
| fall 5% in 4h, target +1.5%, stop -3%, max 24h | 0.50% | $1,089 (50 trades, 82% won) | $1,005 (48 trades, 73% won) | $983 (47 trades, 70% won) |
| fall 5% in 4h, target +1.5%, stop -3%, max 24h | 1.10% | $966 (50 trades, 82% won) | $896 (48 trades, 73% won) | $878 (47 trades, 70% won) |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 0.30% | $1,150 (19 trades, 100% won) | $1,076 (19 trades, 84% won) | $1,033 (18 trades, 72% won) |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 0.50% | $1,133 (19 trades, 100% won) | $1,060 (19 trades, 84% won) | $1,018 (18 trades, 72% won) |
| fall 5% in 1h, target +1.5%, stop -4%, max 24h | 1.10% | $1,082 (19 trades, 100% won) | $1,013 (19 trades, 84% won) | $975 (18 trades, 72% won) |

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
| dip setup: fall 1.5 ATR in 2 days, RSI below 30, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 7 | 29% | -3.26% | -8.18% | $964 | 8.1% | never | never |
| dip setup: fall 1.5 ATR in 2 days, RSI below 45, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 16 | 44% | -0.94% | -8.18% | $991 | 10.8% | never | never |
| dip setup: fall 1.5 ATR in 2 days, RSI below 60, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR | 24 | 25% | -2.36% | -8.18% | $844 | 20.7% | never | 28 Feb 2025 |
| Plan B breakout: close above 20-day high, stop 1.2 ATR, T1 1.2, T2 2.4 ATR | 39 | 51% | -0.05% | -6.16% | $1,041 | 11.6% | 21 Nov 2024 | never |

- dip setup: fall 1.5 ATR in 2 days, RSI below 30, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2024: 3 trades, -1.99% avg, 2025: 3 trades, -2.89% avg, 2026: 1 trades, -8.18% avg.
- dip setup: fall 1.5 ATR in 2 days, RSI below 45, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2024: 6 trades, +0.91% avg, 2025: 8 trades, -2.42% avg, 2026: 2 trades, -0.54% avg.
- dip setup: fall 1.5 ATR in 2 days, RSI below 60, stabilise, stop 1.2 ATR, T1 1.2 / T2 2.4 ATR: 2023: 1 trades, -4.45% avg, 2024: 9 trades, -1.26% avg, 2025: 11 trades, -3.30% avg, 2026: 3 trades, -1.52% avg.
- Plan B breakout: close above 20-day high, stop 1.2 ATR, T1 1.2, T2 2.4 ATR: 2023: 4 trades, +0.62% avg, 2024: 16 trades, +0.42% avg, 2025: 7 trades, +2.73% avg, 2026: 12 trades, -2.51% avg.
