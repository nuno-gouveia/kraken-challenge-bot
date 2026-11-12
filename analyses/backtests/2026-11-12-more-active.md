# Backtest: a more active, more aggressive strategy (01 Oct 2023 to 01 Nov 2026)

BTC, 15-minute candles (Binance archive, research only). Exit slippage 0.3%, no fees. Quiet hours 22:30 to 06:30 Lisbon are modelled: no buys, and an exit due at night happens at the 06:30 price. Challenge runs start at $1,050.60, pass at $1,120, fail when equity touches $950 (inside a trade too). One run starts every week of the history and lasts at most a year; the runs overlap, so read the percentages as a description of the past three years, not as odds.

## 1. Which trigger trades more often and still has an edge

Every rule: buy 15 to 30 minutes after the signal, awake hours only, sell at +2%, at -4% or after 24 hours.

| Rule | Pair | Trades a year | Win | Avg per trade | Avg 2024 / 2025 / 2026 | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| fall 5% in 4h (today) | BTCEUR | 10 | 73% | +0.25% | +0.53% / -0.29% / +0.11% | -4.3% | -6.2% |
| fall 5% in 4h (today) | BTCUSDT | 9 | 76% | +0.46% | +0.67% / -0.03% / +0.10% | -4.3% | -6.1% |
| fall 5% in 6h | BTCEUR | 14 | 73% | +0.11% | +0.01% / -0.37% / +1.04% | -4.3% | -7.4% |
| fall 5% in 6h | BTCUSDT | 14 | 74% | +0.32% | +0.35% / -0.33% / +0.98% | -4.3% | -8.5% |
| fall 4% in 4h | BTCEUR | 23 | 73% | +0.28% | +0.48% / +0.01% / -0.22% | -4.3% | -6.0% |
| fall 4% in 4h | BTCUSDT | 22 | 72% | +0.35% | +0.49% / +0.30% / -0.16% | -4.5% | -7.6% |
| fall 4% in 6h (proposed) | BTCEUR | 30 | 72% | +0.26% | +0.04% / +0.46% / +0.43% | -4.7% | -7.4% |
| fall 4% in 6h (proposed) | BTCUSDT | 30 | 66% | +0.16% | +0.23% / -0.00% / +0.24% | -5.0% | -8.2% |
| fall 3.5% in 6h | BTCEUR | 43 | 64% | -0.03% | +0.10% / -0.14% / -0.36% | -4.9% | -8.4% |
| fall 3.5% in 6h | BTCUSDT | 43 | 64% | -0.02% | +0.07% / +0.14% / -0.75% | -4.8% | -8.6% |
| fall 3% in 4h | BTCEUR | 53 | 64% | +0.05% | -0.09% / +0.21% / -0.45% | -9.8% | -11.7% |
| fall 3% in 4h | BTCUSDT | 52 | 64% | -0.06% | -0.29% / +0.33% / -0.71% | -10.1% | -11.8% |
| fall 3% in 6h | BTCEUR | 59 | 59% | -0.22% | -0.44% / -0.07% / -0.41% | -9.8% | -11.7% |
| fall 3% in 6h | BTCUSDT | 59 | 61% | -0.25% | -0.59% / +0.18% / -0.48% | -10.1% | -11.8% |
| fall 2% in 2h | BTCEUR | 92 | 57% | -0.15% | -0.23% / +0.03% / -0.62% | -6.3% | -9.3% |
| fall 2% in 2h | BTCUSDT | 90 | 56% | -0.23% | -0.34% / -0.02% / -0.77% | -7.1% | -10.7% |

## 2. The exits around the proposed trigger (fall 4% in 6h)

| Rule | Pair | Trades a year | Win | Avg per trade | Avg 2024 / 2025 / 2026 | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| +2% / -4% / 24h | BTCEUR | 30 | 72% | +0.26% | +0.04% / +0.46% / +0.43% | -4.7% | -7.4% |
| +2% / -4% / 24h | BTCUSDT | 30 | 66% | +0.16% | +0.23% / -0.00% / +0.24% | -5.0% | -8.2% |
| +2% / -3% / 24h | BTCEUR | 30 | 68% | +0.19% | +0.08% / +0.11% / +0.50% | -4.4% | -7.4% |
| +2% / -3% / 24h | BTCUSDT | 31 | 61% | -0.02% | +0.02% / -0.27% / +0.27% | -5.0% | -8.2% |
| +2% / -5% / 24h | BTCEUR | 29 | 71% | +0.15% | +0.02% / +0.33% / -0.24% | -5.3% | -7.9% |
| +2% / -5% / 24h | BTCUSDT | 30 | 64% | +0.01% | +0.11% / -0.07% / -0.44% | -5.3% | -8.2% |
| +1.5% / -4% / 24h | BTCEUR | 31 | 75% | +0.12% | -0.01% / +0.37% / -0.00% | -4.4% | -7.4% |
| +1.5% / -4% / 24h | BTCUSDT | 30 | 69% | -0.05% | +0.08% / -0.26% / +0.03% | -5.0% | -8.2% |
| +2.5% / -4% / 24h | BTCEUR | 29 | 67% | +0.27% | +0.14% / +0.30% / +0.42% | -4.7% | -7.4% |
| +2.5% / -4% / 24h | BTCUSDT | 29 | 61% | +0.10% | +0.06% / +0.02% / +0.29% | -8.5% | -10.1% |
| +3% / -4% / 36h | BTCEUR | 28 | 64% | +0.09% | -0.11% / +0.31% / -0.22% | -8.2% | -10.1% |
| +3% / -4% / 36h | BTCUSDT | 27 | 58% | -0.19% | -0.13% / -0.33% / -0.42% | -8.5% | -10.1% |
| +2% / -4% / 12h | BTCEUR | 31 | 63% | +0.14% | +0.07% / +0.08% / +0.40% | -4.4% | -7.4% |
| +2% / -4% / 12h | BTCUSDT | 31 | 58% | +0.01% | +0.21% / -0.43% / +0.18% | -5.0% | -8.2% |
| +2% / -4% / 36h | BTCEUR | 30 | 72% | +0.20% | -0.12% / +0.41% / +0.56% | -4.7% | -7.4% |
| +2% / -4% / 36h | BTCUSDT | 29 | 68% | +0.02% | +0.08% / -0.30% / +0.47% | -5.0% | -8.2% |

## 3. Position size: today's rule (fall 5% in 4h)

Share of the weekly challenge runs that passed, failed or were still open after a year.

| Sizing | First trade | Pair | Passed | Failed | Still open | Passed within 90 days | Median days to pass |
|---|---|---|---|---|---|---|---|
| 40% of the balance (today) | $420 | BTCEUR | 0% | 0% | 100% | 0% | n/a |
| 40% of the balance (today) | $420 | BTCUSDT | 12% | 0% | 88% | 0% | 313 |
| 60% of the balance | $630 | BTCEUR | 25% | 0% | 75% | 0% | 205 |
| 60% of the balance | $630 | BTCUSDT | 28% | 0% | 72% | 0% | 205 |
| 80% of the balance | $840 | BTCEUR | 41% | 5% | 54% | 0% | 176 |
| 80% of the balance | $840 | BTCUSDT | 41% | 0% | 59% | 7% | 162 |
| 100% of the balance | $1,051 | BTCEUR | 42% | 22% | 36% | 10% | 116 |
| 100% of the balance | $1,051 | BTCUSDT | 41% | 0% | 59% | 15% | 106 |
| risk 25% of the room above $950 | $585 | BTCEUR | 33% | 0% | 67% | 0% | 205 |
| risk 25% of the room above $950 | $585 | BTCUSDT | 37% | 0% | 63% | 3% | 173 |
| risk 35% of the room above $950 | $819 | BTCEUR | 42% | 0% | 58% | 3% | 159 |
| risk 35% of the room above $950 | $819 | BTCUSDT | 41% | 0% | 59% | 13% | 127 |
| risk 50% of the room above $950 | $1,051 | BTCEUR | 42% | 0% | 58% | 10% | 116 |
| risk 50% of the room above $950 | $1,051 | BTCUSDT | 41% | 0% | 59% | 15% | 106 |

## 4. Position size: the proposed rule (fall 4% in 6h)

Share of the weekly challenge runs that passed, failed or were still open after a year.

| Sizing | First trade | Pair | Passed | Failed | Still open | Passed within 90 days | Median days to pass |
|---|---|---|---|---|---|---|---|
| 40% of the balance (today) | $420 | BTCEUR | 36% | 0% | 64% | 0% | 236 |
| 40% of the balance (today) | $420 | BTCUSDT | 24% | 0% | 76% | 0% | 239 |
| 60% of the balance | $630 | BTCEUR | 51% | 7% | 41% | 6% | 148 |
| 60% of the balance | $630 | BTCUSDT | 36% | 7% | 57% | 6% | 187 |
| 80% of the balance | $840 | BTCEUR | 51% | 33% | 16% | 28% | 86 |
| 80% of the balance | $840 | BTCUSDT | 43% | 38% | 19% | 13% | 144 |
| 100% of the balance | $1,051 | BTCEUR | 60% | 40% | 0% | 38% | 68 |
| 100% of the balance | $1,051 | BTCUSDT | 42% | 49% | 9% | 16% | 110 |
| risk 25% of the room above $950 | $585 | BTCEUR | 41% | 0% | 59% | 6% | 134 |
| risk 25% of the room above $950 | $585 | BTCUSDT | 28% | 0% | 72% | 7% | 194 |
| risk 35% of the room above $950 | $819 | BTCEUR | 47% | 0% | 53% | 34% | 69 |
| risk 35% of the room above $950 | $819 | BTCUSDT | 33% | 0% | 67% | 13% | 120 |
| risk 50% of the room above $950 | $1,051 | BTCEUR | 48% | 0% | 52% | 36% | 54 |
| risk 50% of the room above $950 | $1,051 | BTCUSDT | 38% | 0% | 62% | 15% | 110 |

## 5. What weakens it

The proposed rule, risking 35% of the room above $950, when reality is less kind than the model.

| Case | Pair | Avg per trade | Passed | Failed | Still open | Passed within 90 days | Median days to pass |
|---|---|---|---|---|---|---|---|
| as modelled | BTCEUR | +0.26% | 47% | 0% | 53% | 34% | 69 |
| as modelled | BTCUSDT | +0.16% | 33% | 0% | 67% | 13% | 120 |
| buy 30 to 45 minutes after the signal | BTCEUR | +0.16% | 45% | 0% | 55% | 25% | 86 |
| buy 30 to 45 minutes after the signal | BTCUSDT | +0.09% | 36% | 0% | 64% | 14% | 102 |
| exit slippage 0.5% | BTCEUR | +0.06% | 39% | 0% | 61% | 20% | 87 |
| exit slippage 0.5% | BTCUSDT | -0.04% | 14% | 0% | 86% | 8% | 84 |
| half the signals missed | BTCEUR | +0.12% | 46% | 0% | 54% | 11% | 147 |
| half the signals missed | BTCUSDT | +0.37% | 48% | 0% | 52% | 17% | 108 |

## 6. For comparison: one big swing

No signal: buy BTC on any day (tried twice a week through the history), sell when equity reaches $1,120, or sell when it falls to the level given.

| Position | Pair | Passed | Median days to pass | Stopped out | Touched $950 |
|---|---|---|---|---|---|
| 100% of the balance, sell if equity falls to $1,000 | BTCEUR | 47% | 5 | 53% | 0% |
| 100% of the balance, sell if equity falls to $1,000 | BTCUSDT | 48% | 5 | 52% | 0% |
| 100% of the balance, sell if equity falls to $985 | BTCEUR | 54% | 7 | 46% | 0% |
| 100% of the balance, sell if equity falls to $985 | BTCUSDT | 54% | 6 | 46% | 0% |
| 100% of the balance, sell if equity falls to $970 | BTCEUR | 61% | 7 | 37% | 1% |
| 100% of the balance, sell if equity falls to $970 | BTCUSDT | 61% | 7 | 39% | 0% |
| 60% of the balance, sell if equity falls to $985 | BTCEUR | 55% | 17 | 45% | 0% |
| 60% of the balance, sell if equity falls to $985 | BTCUSDT | 57% | 17 | 43% | 0% |

## 7. Nights

- BTCEUR: 1115 nights; the worst fall between 22:30 and 06:30 was -10.5%; 16 nights fell more than 5%.
- BTCUSDT: 1115 nights; the worst fall between 22:30 and 06:30 was -10.7%; 13 nights fell more than 5%.
