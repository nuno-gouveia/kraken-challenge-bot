# Strategy and risk framework

Agreed with Nuno on 14 Sep 2026 and refined daily since. **Do not change any rule here without his explicit agreement.** Propose changes in the brief and wait for his reply.

## The challenge

| Item | Value |
|---|---|
| Capital managed | $1,000 of Kraken's funds (entry cost $20, already paid) |
| Pass | **$1,120** (+12%) |
| Fail | **$950**, touched at any time (-5% of initial) |
| Time limit | none |
| Direction | **long only**: buy, then sell. No shorting |
| Assets | BTC, ETH, LINK, BCH, DOGE, SHIB. No stocks |
| Order types | **no stop-loss orders.** Every exit is an alert plus a manual market sell. Assume **0.3% slippage** on an exit |

## The verdict

Every brief gives one verdict: **up / down / don't know**. Recommend a position **only** on high confidence of a short-term move up. "No trade, stay in cash" is a valid and frequent answer. "Don't know" is a valid verdict.

Every recommended position states: asset, entry trigger, size in dollars, **exit (down)**, **T1** and **T2 (up)**, every price in EUR and USD.

## The setup: flash dip (Nuno, 19 to 20 Oct 2026; more active and bigger since 12 Nov 2026)

Replaces the daily-candle dip setup and Plan B entries. Nuno's own observation over years: after a very sharp drop of a few hours, BTC usually bounces, and a buy right after it can be sold within about a day at a small profit. Tested on three years of 15-minute candles (`analyses/backtests/2026-10-19-flash-dip-vs-dip-setup.md`): the dip setup and Plan B lost money; this rule made money across nearby settings, on BTC/EUR and BTC/USDT.

**More aggressive since 12 Nov 2026.** Nuno: the money is virtual, a failed challenge costs another $20 entry, and the first version (5% in 4 hours, $420 a trade) barely traded: about 10 signals a year, about $7 a win. A stricter backtest (`analyses/backtests/2026-11-12-more-active.md`, quiet hours and the $950 floor modelled) showed that version almost never passing within a year. Nuno chose the looser trigger and the bigger size below.

**The rule** (settings in `config/flash.json`):

- **Signal:** BTC/EUR on Kraken falls **4% or more under its highest price of the last 6 hours**. The heartbeat checks every run and sends a BUY message with the plan at once. (A smaller fall has no edge in the backtest: at 3.5% it is gone, at 3% it loses money.)
- **Buy** at market, **only if Nuno can do it within about 15 minutes.** Later, the bounce is usually under way: let it go (tap Not done). Missing signals is fine. Buying 30 to 45 minutes late roughly halves the edge.
- **Size:** 35% of the room above $950 at risk on the stop (see Sizing): about **$810 at $1,050.60**.
- **Exits**, armed by the bot from the real fill price: **sell at +2%**, **exit at -4%**, or **sell after 24 hours**, whichever comes first.
- **Only in awake hours:** no signals between 22:30 and 06:30 Lisbon (Nuno, 19 Oct 2026). One position at a time; one signal per 6-hour window; an unanswered signal lapses after 2 hours.
- Expect about 30 signals a year in awake hours (2 to 3 a month), about 7 in 10 winning. The edge is thin: about +0.2% to +0.3% a trade after slippage, and it moves with small changes in the assumptions. In the backtest, a third to a half of the challenges started at $1,050 passed within a year (typically after 2 to 4 months) and none failed; the rest were still open.

**What the brief and event checks do now:** they don't pick entries. They watch the market, the macro calendar and any open position, report how the flash dip is doing (signals, trades, results against the backtest), and judge whether a sharp drop looks like a flush (forced selling, the rule's case) or a real break (a hack, a ban, more to come). Untested ideas, such as pausing the flash dip before tier-one releases, the other five assets or a second strategy, are proposed in the brief with a backtest and wait for Nuno's answer.

The old dip setup (sharp drop, oversold, stabilisation, buy on daily candles) and Plan B (pullback and breakout entries) are retired: in the backtest every reading of the dip setup lost money, and the breakout was flat at best.

## Sizing (Nuno, 12 Nov 2026)

**Risk per trade: 35% of the room above $950.** That is the loss if the -4% exit is hit, not the position size.

```
room ($)          = balance - 950
risk ($)          = room x 0.35
position size ($) = risk / 0.043      (the 4% stop plus 0.3% slippage), rounded down to $10
```

Never more than the cash. The bot does this sum for every signal (`src/flash.py`) and puts the size and the loss at the exit in the BUY message.

| Balance | Room above $950 | At risk | Position |
|---|---|---|---|
| $975 | $25 | $9 | $200 |
| $1,000 | $50 | $18 | $400 |
| $1,025 | $75 | $26 | $610 |
| **$1,050.60** | $100.60 | $35 | **$810** |
| $1,075 | $125 | $44 | $1,010 |
| $1,085 and above | $135 and more | $47 and more | the whole cash |

The size shrinks after a loss and grows after a win. So a run of losses slows down before it reaches the floor, and a run of wins speeds up towards the target.

- **One position at a time, BTC only.**
- **The finishing trade:** when a +2% win on a smaller position already reaches $1,120, the bot caps the size at that (for example $890 at a balance of $1,105). Take the trade that finishes it rather than a bigger one.
- **Balance touches $975:** stop and reassess with Nuno before the next buy. The rule's sizes are small by then (about $200). The choice is to carry on at those sizes or to let this challenge go and start a fresh one.

### What this accepts (and what it replaced)

The 2% risk per trade, the 40% cap, the escalation ladder and the 15% overnight gap check (which capped total exposure at $600) are retired (Nuno, 12 Nov 2026).

- **Nights.** A position can be open while Nuno sleeps, and no exit acts before 06:30. The worst night in three years of history fell between 10.5% and 10.7% from the 22:30 price; 13 to 16 nights fell more than 5%. At 35% of the room, a night like that from the entry price takes about 85% to 87% of the room and leaves the challenge alive. That is why the share is 35% and not 50%. A worse night than any in the history can end the challenge.
- **A stop costs about a third of the room,** so three stops in a row leave about $978 from $1,050.60.
- The backtest's "none failed" describes three years of history. It is not a promise.

## Hard rules for levels

- **Stop at least 1 ATR from entry.** Never tighten inside 1 ATR. (The post-T1 breakeven exit is exempt.)
- **Targets go just UNDER known resistance, never over.** T1's job is moving the exit to breakeven; T1 sells half.
- **Blended reward:risk must be at least 1:1** (computed with T1 on half and T2 on half). Below that, the plan is not issued, and a standing entry is withdrawn, with the reason stated.
- **Entries get a guard band** (only buy if price is between X and Y when acting) and, around scheduled prints, a **time gate**.
- **Tier-one macro events** (FOMC, CPI, NFP, central-bank decisions): never hold through one unless already past T1 with the exit at breakeven. Turn this into a **date** in the brief, and write the matching "no new entry before" date too.
- **No "up" verdict on a short squeeze.** Judge a move's character by liquidation split (with its time window), open interest and order flow, not only size.
- **Change targets when the levels force it, not when they merely permit it.** A stable alert set is worth more to someone acting from a phone.
- **A level is a hypothesis until tested, a fact once defended, and back to a hypothesis once broken.** One rejection does not make a seller.
- **If a target alert fires and Nuno sees it late, sell at market on sight.** Do not wait for the level to come back.
- **Quiet hours, 22:30 to 06:30 Lisbon (Nuno, 2 Oct 2026).** No action is sent in that window and Nuno is assumed not to act on anything due then. At 06:30 every such action is re-checked against the price: still through its level, he gets the action then; back on the other side, no action, the alert stays armed and the brief re-plans.
- **Breadth matters:** a BTC rally with the other five names flat or down is weak evidence. Read breadth over several days.
- **One session does not vindicate or refute a multi-day call.** Check whether a move stayed before calling it news.

## Brief format (the daily email)

**Changed with Nuno's agreement on 5 Oct 2026: the old brief's layout, made more concise.** The template, length limits and a worked example are in `docs/brief-format.md`. In short:

1. **The action first**, in capitals, then the verdict in one sentence.
2. A compact **account** block: position, price, unrealised P&L, equity, balance and cash, room to target and floor, and the size the next flash-dip buy would have (with its loss at the -4% exit).
3. **What to do, step by step**, numbered and grouped by day. Doing nothing is written as an instruction ("Hold, do not add").
4. **The alerts the bot is watching**, what each one will tell him to do, and what was removed and why.
5. **Why**: price, technicals, flows and sentiment, macro, breadth, one line each.
6. The flash dip, one or two lines. **Reference levels (information only)** on one or two lines.
7. At most 450 words on a busy day, about 250 on a quiet one. Readable on a phone. **No em dash characters.** Ends with "Not financial advice."

