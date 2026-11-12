# Backtest: the other five assets (01 Nov 2023 to 11 Nov 2026)

ETH, LINK, BCH, DOGE and SHIB against USDT, 15-minute candles (Binance archive, research only), with BTC for comparison. Exit slippage 0.3% unless stated, no fees. Quiet hours 22:30 to 06:30 Lisbon are modelled as in `2026-11-12-more-active.md`. "Profit a year, in risks" adds up each trade's result divided by what it would lose at its stop: it compares rules whose stops differ. Many rules were tried here, so a single good row proves little; look for rows that agree.

## 1. How much more they move than BTC

| Asset | Typical 6-hour range | Against BTC | Worst night (22:30 to 06:30) |
|---|---|---|---|
| BTC | 1.4% | 1.00x | -11% |
| ETH | 2.0% | 1.44x | -27% |
| LINK | 2.7% | 1.98x | -25% |
| BCH | 2.4% | 1.73x | -26% |
| DOGE | 2.7% | 1.95x | -25% |
| SHIB | 2.6% | 1.87x | -25% |

The worst nights are 10 Oct 2025, when a liquidation cascade took these coins down 25% to 55% within minutes on Binance. Kraken's prices that night were less extreme, but a position in one of them would have ended the challenge at almost any size.

## 2. The BTC rule on each asset, scaled to its volatility

BTC's rule is: fall 4% in 6 hours, sell at +2%, at -4% or after 24 hours. Each asset gets the same rule with every number multiplied by how much more it moves.

| Rule | Trades a year | Win | Avg per trade | Profit a year, in risks | Avg 2024 / 2025 / 2026 (trades) | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| BTC: fall 4% in 6h, +2% / -4% | 31 | 65% | +0.11% | +0.8 | +0.23% (46) / -0.00% (30) / +0.13% (15) | -5% | -8% |
| ETH: fall 5.8% in 6h, +2.9% / -5.8% | 22 | 58% | -0.54% | -2.0 | -0.47% (20) / -0.28% (37) / -1.65% (10) | -15% | -27% |
| LINK: fall 7.6% in 6h, +3.8% / -7.6% | 21 | 62% | -0.20% | -0.5 | -0.07% (26) / -0.19% (30) / -1.34% (6) | -12% | -26% |
| BCH: fall 7% in 6h, +3.5% / -7% | 22 | 52% | -0.75% | -2.3 | -1.47% (33) / -1.01% (15) / +0.66% (17) | -17% | -27% |
| DOGE: fall 7.6% in 6h, +3.8% / -7.6% | 30 | 62% | -0.30% | -1.1 | -1.18% (45) / +0.31% (34) / +0.91% (8) | -11% | -26% |
| SHIB: fall 7.6% in 6h, +3.8% / -7.6% | 25 | 57% | -0.53% | -1.7 | +0.23% (48) / -2.42% (16) / -1.63% (9) | -13% | -33% |

## 3. On BTC's signal, buy another asset instead

Same moments as the BTC rule (BTC 4% under its 6-hour high), exits scaled to the asset bought.

| Rule | Trades a year | Win | Avg per trade | Profit a year, in risks | Avg 2024 / 2025 / 2026 (trades) | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| buy BTC, +2% / -4% | 31 | 65% | +0.11% | +0.8 | +0.23% (46) / -0.00% (30) / +0.13% (15) | -5% | -8% |
| buy ETH, +2.9% / -5.8% | 29 | 57% | -0.38% | -1.8 | -0.39% (42) / -0.21% (30) / -0.90% (13) | -15% | -23% |
| buy LINK, +3.8% / -7.6% | 29 | 67% | +0.49% | +1.8 | +0.63% (43) / +0.16% (30) / +0.67% (13) | -9% | -18% |
| buy BCH, +3.5% / -7% | 29 | 62% | +0.13% | +0.5 | -0.33% (42) / +0.13% (30) / +1.44% (13) | -12% | -20% |
| buy DOGE, +3.8% / -7.6% | 30 | 62% | -0.02% | -0.1 | +0.19% (46) / -0.81% (29) / +0.92% (13) | -9% | -14% |
| buy SHIB, +3.8% / -7.6% | 28 | 59% | -0.14% | -0.5 | -0.09% (44) / -0.73% (27) / +0.80% (13) | -10% | -17% |

## 4. Only the extreme falls

LINK, BCH, DOGE and SHIB together, one position at a time: the asset falls X in W hours, sell at +X/2, at -X or after 24 hours.

| Rule | Trades a year | Win | Avg per trade | Profit a year, in risks | Avg 2024 / 2025 / 2026 (trades) | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| fall 6% in 2h | 47 | 62% | -0.23% | -1.8 | -0.26% (84) / -0.02% (40) / -0.65% (18) | -11% | -53% |
| fall 8% in 2h | 17 | 66% | +0.79% | +1.7 | -0.32% (40) / +5.36% (8) / +2.06% (4) | -9% | -17% |
| fall 9% in 2h | 11 | 75% | +2.46% | +2.8 | +1.74% (26) / +9.29% (3) / +0.68% (2) | -9% | -14% |
| fall 10% in 2h | 9 | 77% | +3.27% | +2.7 | +2.07% (22) / +32.98% (1) / +0.93% (2) | -10% | -16% |
| fall 12% in 2h | 4 | 77% | +5.00% | +1.7 | +2.66% (12) / +32.98% (1) / none | -12% | -25% |
| fall 6% in 4h | 73 | 58% | -0.30% | -3.4 | -0.48% (112) / -0.19% (71) / -0.52% (28) | -9% | -20% |
| fall 8% in 4h | 31 | 61% | +0.05% | +0.2 | -0.19% (61) / +0.10% (21) / +0.86% (12) | -11% | -56% |
| fall 9% in 4h | 17 | 68% | +1.52% | +2.9 | +0.98% (38) / +3.24% (9) / +1.97% (5) | -9% | -25% |
| fall 10% in 4h | 13 | 75% | +2.33% | +3.0 | +1.94% (31) / +4.41% (6) / +0.93% (2) | -10% | -25% |
| fall 12% in 4h | 7 | 76% | +3.18% | +1.8 | +1.69% (20) / +32.98% (1) / none | -12% | -25% |
| fall 6% in 6h | 95 | 59% | -0.23% | -3.4 | -0.21% (145) / -0.23% (90) / -0.50% (39) | -9% | -20% |
| fall 8% in 6h | 41 | 56% | -0.58% | -2.9 | -1.14% (65) / -0.34% (39) / +0.31% (16) | -11% | -26% |
| fall 9% in 6h | 29 | 57% | +0.00% | +0.0 | -0.18% (54) / -0.12% (21) / +0.99% (11) | -9% | -25% |
| fall 10% in 6h | 19 | 67% | +0.82% | +1.5 | +1.26% (39) / -1.59% (10) / +1.25% (7) | -10% | -53% |
| fall 12% in 6h | 11 | 78% | +2.51% | +2.2 | +3.17% (24) / +0.03% (6) / -1.40% (1) | -12% | -56% |

The same at the two thresholds that look best, under harder assumptions:

| Rule | Trades a year | Win | Avg per trade | Profit a year, in risks | Avg 2024 / 2025 / 2026 (trades) | Worst trade | Worst dip while held |
|---|---|---|---|---|---|---|---|
| fall 9% in 4h, slippage 0.6% | 17 | 66% | +1.22% | +2.2 | +0.68% (38) / +2.94% (9) / +1.67% (5) | -10% | -25% |
| fall 9% in 4h, without 10 and 11 Oct 2025 | 17 | 67% | +0.91% | +1.7 | +0.98% (38) / -0.47% (8) / +1.97% (5) | -9% | -25% |
| fall 10% in 4h, slippage 0.6% | 13 | 75% | +2.03% | +2.5 | +1.64% (31) / +4.11% (6) / +0.63% (2) | -11% | -25% |
| fall 10% in 4h, without 10 and 11 Oct 2025 | 13 | 74% | +1.54% | +1.9 | +1.94% (31) / -1.30% (5) / +0.93% (2) | -10% | -25% |

Fall 10% in 4h, trades by asset over the whole period: LINK 13, BCH 3, DOGE 13, SHIB 11.

## 5. Added to the BTC rule: challenge runs

Weekly challenge starts from $1,050.60, one year each, 35% of the room above $950 at risk on each trade's own stop, one position at a time across all assets.

| Rules | Trades a year | Passed | Failed | Still open | Passed within 90 days | Median days to pass |
|---|---|---|---|---|---|---|
| BTC rule alone | 31 | 36% | 0% | 64% | 12% | 124 |
| BTC rule + fall 10% in 4h on LINK, BCH, DOGE, SHIB | 38 | 78% | 0% | 22% | 45% | 74 |
| BTC rule + fall 9% in 4h on LINK, BCH, DOGE, SHIB | 40 | 81% | 0% | 19% | 44% | 80 |
| the same, 10% in 4h, without 10 and 11 Oct 2025 | 37 | 51% | 0% | 49% | 37% | 63 |
