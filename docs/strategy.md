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

## The setup: flash dip (Nuno, 19 to 20 Oct 2026)

Replaces the daily-candle dip setup and Plan B entries. Nuno's own observation over years: after a very sharp drop of a few hours, BTC usually bounces, and a buy right after it can be sold within about a day at a small profit. Tested on three years of 15-minute candles (`analyses/backtests/2026-10-19-flash-dip-vs-dip-setup.md`): the dip setup and Plan B lost money; this rule made money across nearby settings, on BTC/EUR and BTC/USDT.

**The rule** (settings in `config/flash.json`):

- **Signal:** BTC/EUR on Kraken falls **5% or more under its highest price of the last 4 hours**. The heartbeat checks every run and sends a BUY message with the plan at once.
- **Buy** at market, **only if Nuno can do it within about 15 minutes.** Later, the bounce is usually under way: let it go (tap Not done). Missing signals is fine.
- **Size:** 2% of the balance at risk on the 4% stop, capped at 40% of the balance (about $420 at $1,055).
- **Exits**, armed by the bot from the real fill price: **sell at +2%**, **exit at -4%**, or **sell after 24 hours**, whichever comes first.
- **Only in awake hours:** no signals between 22:30 and 06:30 Lisbon (Nuno, 19 Oct 2026). One position at a time; one signal per 4-hour window; an unanswered signal lapses after 2 hours.
- Expect about 10 signals a year in awake hours, about 8 in 10 winning (+2%) and the rest exiting at -4% or after 24 hours.

**What the brief and event checks do now:** they don't pick entries. They watch the market, the macro calendar and any open position, report how the flash dip is doing (signals, trades, results against the backtest), and judge whether a sharp drop looks like a flush (forced selling, the rule's case) or a real break (a hack, a ban, more to come). Untested ideas, such as pausing the flash dip before tier-one releases or a second strategy, are proposed in the brief with a backtest and wait for Nuno's answer.

The old dip setup (sharp drop, oversold, stabilisation, buy on daily candles) and Plan B (pullback and breakout entries) are retired: in the backtest every reading of the dip setup lost money, and the breakout was flat at best.

## Sizing

**Risk per trade: 2% of balance** (at $1,050: $21). That is the loss if the exit is hit, not the position size.

```
position size ($) = (balance x 0.02) / (stop distance as a decimal)
```

Then apply the caps.

### Survival check (binds first)

```
total exposure x 0.15  must leave  balance - that loss  above $960
```

A 15% gap is the realistic worst case for a flash crash where the exit cannot be acted on in time. Run it on **combined** exposure (BTC and ETH move together). At $1,050 total exposure is capped at **$600**, so **one $420 position at a time**.

### Escalation ladder

| Balance | Max single (BTC/ETH) | Max single (LINK, BCH) | Max (DOGE, SHIB) | Risk per trade |
|---|---|---|---|---|
| below $1,000 | 25% | 20% | 15% | 1% |
| $1,000 to $1,074 | **40%** | 30% | 20% | 2% |
| $1,075 to $1,119 | 50% | 35% | 25% | 2% |

The survival check overrides the table. Max 2 positions ever; **never all-in**.

### Circuit breaker

Balance touches **$975**: stop trading, reassess, drop to 1% risk for the next three trades. Inside $20 of the target: take the trade that finishes it rather than a bigger one.

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
2. A compact **account** block: position, price, unrealised P&L, equity, balance and cash, room to target and floor. The survival check whenever a buy or add is on the table.
3. **What to do, step by step**, numbered and grouped by day. Doing nothing is written as an instruction ("Hold, do not add").
4. **The alerts the bot is watching**, what each one will tell him to do, and what was removed and why.
5. **Why**: price, technicals, flows and sentiment, macro, breadth, one line each.
6. The flash dip, one or two lines. **Reference levels (information only)** on one or two lines.
7. At most 450 words on a busy day, about 250 on a quiet one. Readable on a phone. **No em dash characters.** Ends with "Not financial advice."

