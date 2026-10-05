# Daily brief: format

Agreed with Nuno on 5 Oct 2026: **the old brief's layout, made shorter.** The action comes first in capitals, then a compact account block, the steps, the alerts, and only then the reasons, one line each. The brief tells him what to do and why in a few words; it doesn't argue its case.

## Length

- **Quiet day** (nothing fired, nothing to do): about 250 words.
- **Busy day** (an alert fired, a fill, a new plan): **at most 450 words**, sources and reference levels included.
- One line per bullet. No paragraph of more than two sentences anywhere.
- If something needs a longer explanation (a data conflict, a rule question), give the conclusion in one line and offer the detail: "Ask me for the detail."
- Don't repeat a number or a reason. Each one appears once, in its section.
- Don't explain how you got a number unless sources disagree. Then say it in one line: "Kraken and CoinGecko differ by EUR 80; used Kraken."

## Subject

`BTC brief <D Mon> - <ACTION>: <reason in at most 8 words>`

Examples: `BTC brief 5 Oct - SELL HALF: T1 at EUR 77,050 fired` · `BTC brief 6 Oct - HOLD: nothing fired, change nothing`

In shadow mode, prefix `[NEW SYSTEM, compare only] `.

## Body, in this order

```
ACTION: <ONE INSTRUCTION, CAPITALS>. <one short follow-up if needed>
Verdict: UP / DOWN / DON'T KNOW. <one sentence>

ACCOUNT
Position: <what he holds, or "none, all cash">
BTC now: $<usd> / EUR <eur> (<24h %>)
Unrealised: <+/-$> (<%>)  |  Equity: ~$<n>
Balance $<n>, cash $<n>
To target: $<n>  |  Above floor: $<n>

SINCE YESTERDAY   (only if something happened; at most 3 lines)
- <alert fired, fill reported, held overnight and how 06:30 went>

WHAT TO DO
Today (<Day D Mon>)
1. <instruction>
This week
2. <date, time Lisbon: event, tier one or not, what to do>
Before <next tier-one date>
3. <the rule turned into a date>

ALERTS THE BOT IS WATCHING
- <below|above> EUR <n> / $<n>: <what he'll be told>
- at <D Mon HH:MM>: <what he'll be told>
Removed: <id or level>: <reason in a few words>

WHY
- Price: <one line>
- Technicals: <RSI, trend, momentum, one line>
- Flows and sentiment: <one line>
- Macro: <next prints, one line>
- Breadth: <one line>

SETUPS
- Dip setup: <n> of 4 (missing: <steps>).
- Plan B: <pullback: issued or not, why in a few words>; <breakout: same>.
- Waiting for your answer: <open question in one line, only if one is open>

REFERENCE LEVELS (information only, not alerts)
<level EUR / $, level EUR / $, ... on one or two lines>

EUR/USD <rate> (<source>). Prices: <Kraken snapshot HH:MM / web, not Kraken>.
Report fills on Telegram: /bought <usd> at <price>, /sold half|all at <price>.
Sources: <at most 3 links>
Not financial advice.
```

Rules carried over from `docs/strategy.md`: every price Nuno might act on in EUR and USD, Lisbon times, a survival check line in ACCOUNT whenever a buy or add is on the table, no em dash, ends with "Not financial advice."

## Example: 5 Oct 2026, written after the half sale was reported (about 370 words; the old brief that day was about 1,900 before its sources)

Subject: `BTC brief 5 Oct - HOLD THE HALF: T1 done, exit now at breakeven`

```
ACTION: HOLD THE OTHER HALF. Your exit is now at breakeven; buy nothing.
Verdict: DON'T KNOW. The push to $87,000 was mostly shorts being squeezed.

ACCOUNT
Position: 0.0024980 BTC (half), bought for $210 at $84,065
BTC now: $86,581 / EUR 77,505 (+2.1%)
Unrealised: +$6.28 (+3.0%)  |  Equity: ~$1,061.54
Balance $1,055.26, cash $845.26
To target: $58.46  |  Above floor: $111.54

SINCE YESTERDAY
- T1 (EUR 77,050) fired at 07:55. You sold half at $86,170: +$5.26.
- The bot moved your exit to breakeven and cancelled the CPI sell.

WHAT TO DO
Today (Mon 5 Oct)
1. Hold the other half. Do not add, do not buy anything else.
This week
2. Wed 7 Oct, 18:01 and 19:00: 10-year auction, then Fed minutes. Not tier one; the main risk to the half.
Before Wed 14 Oct (CPI, 14:30)
3. Nothing to do: you are past T1 with the exit at breakeven, so the half may stay through CPI.

ALERTS THE BOT IS WATCHING
- below EUR 74,600 / $83,336: SELL ALL the BTC you still hold (breakeven exit)
- above EUR 78,200 / $87,357: SELL ALL the BTC you still hold (T2, trade complete)
Removed: exit EUR 72,800 and warning EUR 73,300 (replaced by breakeven); CPI sells (past T1).

WHY
- Price: up 2.1%; $87,000 turned price away twice in four sessions.
- Technicals: RSI 68, near overbought; trend up; MACD flat.
- Flows and sentiment: 88% of liquidations were shorts; ETF inflows cooling; Fear and Greed 70.
- Macro: 10-year yield 5.24%, near a 24-year high; CPI Wed 14 Oct.
- Breadth: improved, four of six coins up on the week.

SETUPS
- Dip setup: 0 of 4 (no drop, not oversold).
- Plan B: pullback 0.95:1, under the 1:1 minimum; breakout leaves no room for a legal stop. Neither issued.
- Waiting for your answer: keep the RSI-below-60 bar, or switch to RSI below 45 plus a 1.5 ATR two-day fall?

REFERENCE LEVELS (information only, not alerts)
R2 EUR 77,881 / $87,000 · R1 EUR 76,520 / $85,480 · S1 EUR 75,336 / $84,158 · Entry EUR 74,613 / $84,065

EUR/USD 1.1171 (Kraken XBTUSD/XBTEUR). Prices: Kraken, 08:20 Lisbon.
Report fills on Telegram: /bought <usd> at <price>, /sold half|all at <price>.
Not financial advice.
```
