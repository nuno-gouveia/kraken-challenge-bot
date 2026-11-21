# Backtest: buy the flash dip only after a down week (01 Oct 2023 to 11 Nov 2026)

## Verdict (Claude, 21 Nov 2026)

**On BTC the filter looks real, but the case is moderate, not proven. Nothing is changed until Nuno decides.**

For it:
- Every window (3, 7, 14 days) and every line (0% to -10%) improves the average trade on both BTC/EUR and BTC/USDT (section 1). It does not hinge on one lucky setting.
- The trades it skips lose money on both pairs: -0.26% and -0.30% a trade, 64% and 57% wins (section 2).
- It holds in each half of the history separately (section 3).
- A random filter dropping as many trades matches it only 3% (BTC/EUR) and 6% (BTC/USDT) of the time (section 4).
- Challenge runs from $1,050.60 passed within a year more often: 68% against 46% on BTC/EUR, 50% against 32% on BTC/USDT (section 6).

Against it:
- The idea came from this same data, and several settings were tried, so some of the edge is likely luck. The permutation figures are close to the 5% line, not far under it.
- The other five assets do not confirm it (section 5): only DOGE improves, ETH is flat, LINK, BCH and SHIB get worse. The rule loses money on all five anyway, so this is a weak test, but it is not support.
- It trades less: about 18 times a year instead of 30, so a pass takes longer when it comes (median 162 days against 69 on BTC/EUR) and fewer runs pass within 90 days (23% against 33%).
- It would not have saved either recent loss. Trade 3 (5 Nov) came after a 7-day fall of about 7.6%, trade 4 (20 Nov) after about 15.5%: both would have been bought.

The 14-day / -5% line scores best on BTC/EUR, but it was picked out after seeing the results; 7 days / -5% was the line stated before the test, so that is the one to judge.

Today's rule (fall 4% in 6h, sell at +2%, -4% or after 24h), with one extra condition: buy only when BTC's change over the past N days, read on the signal candle, is at or under a line. 15-minute candles (Binance archive), exit slippage 0.3%, quiet hours modelled, the $950 floor checked inside each trade. The first 14 days of history are skipped by every row so all rows cover the same period. Research only.

## 1. Every nearby window and line

If the effect is real, nearby settings should agree, not only 7 days and -5%.

| Filter | Pair | Trades a year | Win | Avg per trade | Avg 2023 / 2024 / 2025 / 2026 | Stopped |
|---|---|---|---|---|---|---|
| none (today) | BTCEUR | 31 | 71% | +0.25% | +0.50% / +0.04% / +0.46% / +0.34% | 18 |
| none (today) | BTCUSDT | 31 | 65% | +0.14% | +0.20% / +0.23% / -0.00% / +0.13% | 17 |
| 3d change at or under +0% | BTCEUR | 24 | 72% | +0.38% | -1.30% / +0.27% / +0.66% / +0.34% | 12 |
| 3d change at or under +0% | BTCUSDT | 24 | 63% | +0.09% | -4.30% / +0.23% / +0.05% / +0.13% | 14 |
| 3d change at or under -3% | BTCEUR | 21 | 73% | +0.39% | -1.30% / +0.21% / +0.63% / +0.55% | 12 |
| 3d change at or under -3% | BTCUSDT | 19 | 65% | +0.08% | -4.30% / +0.13% / +0.10% / +0.32% | 13 |
| 3d change at or under -5% | BTCEUR | 16 | 76% | +0.57% | +1.70% / +0.37% / +0.71% / +0.62% | 9 |
| 3d change at or under -5% | BTCUSDT | 15 | 66% | +0.11% | n/a / +0.03% / -0.18% / +0.57% | 10 |
| 3d change at or under -7.5% | BTCEUR | 10 | 84% | +0.95% | n/a / +0.87% / +1.08% / +0.95% | 5 |
| 3d change at or under -7.5% | BTCUSDT | 9 | 79% | +0.95% | n/a / +1.10% / +0.92% / +0.67% | 4 |
| 3d change at or under -10% | BTCEUR | 6 | 89% | +1.14% | n/a / +0.84% / +1.78% / +0.95% | 2 |
| 3d change at or under -10% | BTCUSDT | 6 | 78% | +0.75% | n/a / +1.06% / +0.40% / +0.67% | 3 |
| 7d change at or under +0% | BTCEUR | 23 | 75% | +0.48% | +1.70% / +0.38% / +0.52% / +0.53% | 12 |
| 7d change at or under +0% | BTCUSDT | 23 | 68% | +0.24% | n/a / +0.45% / -0.02% / +0.30% | 13 |
| 7d change at or under -3% | BTCEUR | 19 | 75% | +0.54% | n/a / +0.71% / +0.45% / +0.44% | 10 |
| 7d change at or under -3% | BTCUSDT | 20 | 68% | +0.23% | n/a / +0.60% / -0.07% / +0.20% | 12 |
| 7d change at or under -5% | BTCEUR | 18 | 77% | +0.66% | n/a / +0.70% / +0.75% / +0.44% | 8 |
| 7d change at or under -5% | BTCUSDT | 18 | 72% | +0.48% | n/a / +0.69% / +0.45% / +0.20% | 8 |
| 7d change at or under -7.5% | BTCEUR | 14 | 80% | +0.72% | n/a / +0.57% / +1.05% / +0.44% | 6 |
| 7d change at or under -7.5% | BTCUSDT | 15 | 78% | +0.65% | n/a / +0.69% / +0.71% / +0.49% | 8 |
| 7d change at or under -10% | BTCEUR | 11 | 85% | +1.08% | n/a / +1.36% / +1.23% / +0.37% | 4 |
| 7d change at or under -10% | BTCUSDT | 10 | 78% | +0.72% | n/a / +1.24% / +0.31% / +0.32% | 5 |
| 14d change at or under +0% | BTCEUR | 23 | 75% | +0.43% | +1.70% / +0.20% / +0.61% / +0.28% | 12 |
| 14d change at or under +0% | BTCUSDT | 23 | 66% | +0.17% | +1.70% / +0.26% / +0.03% / +0.13% | 13 |
| 14d change at or under -3% | BTCEUR | 19 | 80% | +0.75% | n/a / +0.85% / +0.83% / +0.44% | 8 |
| 14d change at or under -3% | BTCUSDT | 20 | 69% | +0.39% | n/a / +0.62% / +0.21% / +0.28% | 10 |
| 14d change at or under -5% | BTCEUR | 19 | 81% | +0.77% | n/a / +0.96% / +0.79% / +0.44% | 8 |
| 14d change at or under -5% | BTCUSDT | 19 | 74% | +0.52% | n/a / +1.00% / +0.26% / +0.17% | 9 |
| 14d change at or under -7.5% | BTCEUR | 16 | 80% | +0.82% | n/a / +1.30% / +0.79% / +0.29% | 7 |
| 14d change at or under -7.5% | BTCUSDT | 17 | 75% | +0.67% | n/a / +1.28% / +0.47% / +0.18% | 7 |
| 14d change at or under -10% | BTCEUR | 12 | 83% | +0.88% | n/a / +1.28% / +0.96% / +0.31% | 5 |
| 14d change at or under -10% | BTCUSDT | 11 | 74% | +0.59% | n/a / +1.40% / +0.28% / +0.02% | 6 |

## 2. The trades the 7d / -5% filter would skip

The other side of the same split: dips that came in a week down less than 5%, or up.

| Trades | Pair | Count | Win | Avg per trade | Stopped |
|---|---|---|---|---|---|
| kept | BTCEUR | 56 | 77% | +0.66% | 8 |
| skipped | BTCEUR | 44 | 64% | -0.26% | 11 |
| kept | BTCUSDT | 54 | 72% | +0.48% | 8 |
| skipped | BTCUSDT | 44 | 57% | -0.30% | 10 |

## 3. Each half of the history on its own

| Filter | Pair | Half | Trades | Win | Avg per trade |
|---|---|---|---|---|---|
| none (today) | BTCEUR | first | 67 | 72% | +0.22% |
| none (today) | BTCEUR | second | 27 | 70% | +0.34% |
| 7d change at or under -5% | BTCEUR | first | 33 | 79% | +0.76% |
| 7d change at or under -5% | BTCEUR | second | 23 | 74% | +0.53% |
| none (today) | BTCUSDT | first | 70 | 66% | +0.16% |
| none (today) | BTCUSDT | second | 25 | 64% | +0.09% |
| 7d change at or under -5% | BTCUSDT | first | 32 | 75% | +0.58% |
| 7d change at or under -5% | BTCUSDT | second | 22 | 68% | +0.32% |

## 4. Could a random filter do as well?

Drop as many trades as the filter does, at random, 20,000 times. The share of those random picks whose average is at least as good as the filter's. Under 5% suggests the filter picks better than luck; around 50% means it does not.

| Filter | Pair | Kept | Avg kept | Avg of all | Random picks as good |
|---|---|---|---|---|---|
| 7d change at or under -5% | BTCEUR | 56 | +0.66% | +0.25% | 3.4% |
| 7d change at or under -3% | BTCEUR | 60 | +0.54% | +0.25% | 4.8% |
| 14d change at or under -5% | BTCEUR | 57 | +0.77% | +0.25% | 0.7% |
| 3d change at or under -3% | BTCEUR | 64 | +0.39% | +0.25% | 6.9% |
| 7d change at or under -5% | BTCUSDT | 54 | +0.48% | +0.14% | 5.8% |
| 7d change at or under -3% | BTCUSDT | 62 | +0.23% | +0.14% | 14.0% |
| 14d change at or under -5% | BTCUSDT | 57 | +0.52% | +0.14% | 3.2% |
| 3d change at or under -3% | BTCUSDT | 60 | +0.08% | +0.14% | 25.3% |

## 5. The other five assets (never looked at for this question)

The rule scaled to each asset's volatility as in `src/backtest_assets.py`; the filter is the same 7-day / -5% line on that asset's own price.

| Asset | Filter | Trades a year | Win | Avg per trade | Random picks as good |
|---|---|---|---|---|---|
| ETH | none | 22 | 58% | -0.54% |  |
| ETH | 7d at or under -5% | 16 | 59% | -0.53% | 48.9% |
| LINK | none | 21 | 62% | -0.26% |  |
| LINK | 7d at or under -5% | 15 | 57% | -0.92% | 77.7% |
| BCH | none | 22 | 52% | -0.81% |  |
| BCH | 7d at or under -5% | 13 | 55% | -0.73% | 67.4% |
| DOGE | none | 30 | 61% | -0.34% |  |
| DOGE | 7d at or under -5% | 15 | 70% | +0.34% | 20.8% |
| SHIB | none | 25 | 56% | -0.57% |  |
| SHIB | 7d at or under -5% | 12 | 62% | -0.74% | 54.8% |

## 6. The challenge: does trading less but better pass more often?

Sized to risk 35% of the room above $950, from $1,050.60. One run starts every week with a year of history ahead; the runs overlap, so read these as a description of the past, not as odds.

| Filter | Pair | Passed | Failed | Still open | Passed within 90 days | Median days to pass |
|---|---|---|---|---|---|---|
| none (today) | BTCEUR | 46% | 0% | 54% | 33% | 69 |
| none (today) | BTCUSDT | 32% | 0% | 68% | 13% | 120 |
| 7d change at or under +0% | BTCEUR | 66% | 0% | 34% | 20% | 150 |
| 7d change at or under +0% | BTCUSDT | 43% | 0% | 57% | 14% | 138 |
| 7d change at or under -3% | BTCEUR | 68% | 0% | 32% | 19% | 177 |
| 7d change at or under -3% | BTCUSDT | 37% | 0% | 63% | 11% | 175 |
| 7d change at or under -5% | BTCEUR | 68% | 0% | 32% | 23% | 162 |
| 7d change at or under -5% | BTCUSDT | 50% | 0% | 50% | 10% | 227 |
| 7d change at or under -7.5% | BTCEUR | 52% | 0% | 48% | 22% | 105 |
| 7d change at or under -7.5% | BTCUSDT | 92% | 0% | 8% | 19% | 167 |
| 14d change at or under -5% | BTCEUR | 82% | 0% | 18% | 27% | 119 |
| 14d change at or under -5% | BTCUSDT | 42% | 0% | 58% | 15% | 105 |
