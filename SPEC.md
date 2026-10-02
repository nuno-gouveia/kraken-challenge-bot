# Build spec

## Goal

Nuno should never again have to type a price alert into Kraken or watch a chart. He gets:

- a **Telegram message the moment he has to do something** (buy, sell, sell half), with the exact instruction and both currencies;
- a **quiet Telegram note** for "watch" alerts that need no action;
- the **daily email at 08:00 Lisbon** explaining the plan, as today;
- a way to **tell the system what he did** ("bought 420 at 84065") from the same Telegram chat.

## Architecture

```
            every 5 min (GitHub Actions)                 07:00 UTC daily (Claude Code scheduled task)
┌──────────────────────────────────────────┐        ┌──────────────────────────────────────────────┐
│ heartbeat.py                             │        │ Claude daily brief                           │
│  1. read Telegram updates (Nuno's        │        │  1. git pull; read state/ + data/snapshot    │
│     reports, button presses)             │        │  2. research news/macro/sentiment (web)      │
│  2. fetch Kraken 1-min OHLC since        │        │  3. decide verdict + plan (docs/strategy.md) │
│     each alert was armed                 │        │  4. write state/alerts.json + analyses/      │
│  3. fire alerts -> Telegram              │        │  5. commit + push                            │
│  4. commit state/ only if it changed     │        │  6. email the brief (Gmail connector)        │
└──────────────────────────────────────────┘        └──────────────────────────────────────────────┘
          ▲                    │                                        │
          │                    ▼                                        ▼
     Kraken API          Telegram bot  ◄──── push to state/alerts.json triggers notify.py
                                              ("today's alerts are set: ...")

            06:45 UTC daily (GitHub Actions): snapshot.py -> data/snapshot.json (indicators from Kraken OHLC)
```

Why this split: an AI session every 5 minutes would be slow, costly and less reliable (the old setup's weekly review hung twice). The script is deterministic and cheap; Claude only runs where judgement is needed.

Why the snapshot job: Claude's cloud sessions cannot reach Kraken's API (the egress proxy blocks it). GitHub Actions can. So Actions fetches the data and commits it, and Claude reads the file. This also ends the old setup's biggest time sink: scraping price pages that were often stale.

## Secrets (GitHub repo > Settings > Secrets and variables > Actions)

| Secret | Required | Notes |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | From @BotFather |
| `TELEGRAM_CHAT_ID` | yes | Nuno's chat id. He gets it by messaging the bot, then opening `https://api.telegram.org/bot<TOKEN>/getUpdates` in his own browser. Never print it in a workflow log |
| `CMC_API_KEY` | optional | CoinMarketCap, fallback price only |

The bot must **only** act on messages from `TELEGRAM_CHAT_ID`. Anything else is ignored silently (not logged in content).

## State files

### `state/alerts.json`

```json
{
  "updated_at": "2026-10-02T18:47:00Z",
  "updated_by": "claude",
  "eur_usd": 1.1268,
  "alerts": [
    {
      "id": "btc-exit",
      "pair": "XBTEUR",
      "direction": "below",
      "level": 72800,
      "level_usd_ref": 82031,
      "kind": "action",
      "message": "SELL ALL your BTC at market now.",
      "status": "armed",
      "armed_at": "2026-10-02T18:47:00Z",
      "valid_from": null,
      "valid_until": null,
      "guard_band": null,
      "on_done": { "arm": [], "disarm": ["btc-warning", "btc-t1", "btc-t2"] }
    }
  ]
}
```

- `direction`: `below` fires when any 1-minute candle **low** since `armed_at` is `<= level`; `above` when any **high** is `>= level`.
- `kind`: `action` (loud Telegram notification, buttons "Done" / "Not done") or `watch` (silent notification, no buttons).
- `status`: `armed` → `fired` → (`done` | `skipped`), or `disabled`. An alert fires **once**. Re-arming means Claude writes it again with a new `armed_at`. An action alert hit during quiet hours becomes `held` (see Quiet hours).
- `valid_from` / `valid_until`: time gate (UTC). Outside it, a firing is reported as "level touched, but NOT authorised now" and the alert stays armed. Used for the rule "no new entry before a tier-one print".
- `guard_band`: `[low, high]` for entry alerts. The message includes the current price and says plainly "only buy if Kraken shows between X and Y; below X do NOT buy".
- `on_done`: what happens when Nuno presses **Done** or reports the trade. E.g. T1 done arms the breakeven exit and disarms the original exit. Follow-ups are armed only on his confirmation, never automatically on the price alone.
- `level_usd_ref`: the USD equivalent at the time it was set, for the message only. Messages also show the USD equivalent at the live rate.

### `state/account.json`

Balance, cash, positions, last confirmation and its channel. See the seed file. The heartbeat updates it from Telegram reports; nothing else infers a fill.

### `state/inbox.jsonl`

One JSON object per line: `{"ts": ..., "text": ..., "parsed": ...}`. Every message from Nuno, verbatim, including ones the parser did not understand (those also get a reply: "I didn't understand that, I've saved it for the next brief").

### `data/snapshot.json`

Written by `snapshot.py`. For each of BTC, ETH, LINK, BCH, DOGE, SHIB, in USD and EUR where Kraken lists the pair: last price, 24h high/low/change, 7d change, and daily RSI14, ATR14 (absolute and %), EMA20/50/200, Bollinger(20,2), MACD(12,26,9). Plus the implied EUR/USD rate from XBTUSD/XBTEUR, and the fetch timestamp. Indicators computed from **closed** daily candles only (the open candle is reported separately) so the RSI does not lag or jump.

## Kraken API notes

- Ticker: `GET https://api.kraken.com/0/public/Ticker?pair=XBTEUR` (fields `c` last, `h`/`l` today and 24h, `b`/`a` bid/ask). No key needed.
- OHLC: `GET https://api.kraken.com/0/public/OHLC?pair=XBTEUR&interval=1&since=<unix>`. Rows are `[time, open, high, low, close, vwap, volume, count]`. Returns at most 720 rows; the result key is the pair's internal name (e.g. `XXBTZEUR`) plus `last`.
- The old setup noted that Kraken's OHLC endpoint once returned a cached window on repeat calls. Sanity check every response: the newest candle must be within ~3 minutes of now, otherwise treat the fetch as failed.
- Failure handling: retry once after 5 s; then try CoinMarketCap (labelled "fallback, not Kraken"); if both fail for **3 consecutive runs**, send one Telegram message "I can't read prices right now, your alerts are NOT being watched" and one "back online" message when it recovers. Never go silent.

## Telegram

- Outbound via `sendMessage` (HTML parse mode). Action alerts: loud, with an inline keyboard (Done / Not done). Watch alerts: `disable_notification: true`.
- **Quiet hours, 22:30 to 06:30 Lisbon** (Nuno, 2 Oct 2026). No action message is sent in that window. The alert becomes `held` (`held_at`, `held_first_touch_at`) and Nuno is assumed **not** to have acted. The first run from 06:30 re-checks every held action, plus any action alert first touched overnight that no run saw: each is armed again with `armed_at` = 06:30 and `held_overnight` recorded. Nuno gets one "Morning update" listing them; an action whose price is still through its level at the re-check is sent right after it as a normal action message, otherwise it stays armed and the daily brief re-plans. Watch alerts and "not authorised" notes still go out at night (they are silent); outage and alerts-file messages are sent silently at night.
- Inbound by polling `getUpdates` with an `offset` at the start of each heartbeat run (no webhook needed). Store the last `update_id` in `state/telegram_offset.json`.
- Commands (also accept plain text, e.g. "Bought 420$ at 84065$"):
  - `/bought <usd> at <price_usd>` (optionally `<asset>`, default BTC)
  - `/sold <all|half|usd> at <price_usd>`
  - `/status`: balance, cash, position, unrealised P&L, distance to target and floor
  - `/alerts`: armed alerts with both currencies and distance from price
  - `/price`
- After a report: update `state/account.json`, apply the alert's `on_done`, append to `inbox.jsonl`, reply with the new state and any alerts just armed or disarmed, commit.
- Message style: short, the action first, both currencies, Lisbon time. No em dash. Example:

  > **ACTION: SELL ALL BTC NOW**
  > Exit alert hit: BTC/EUR touched EUR 72,800 (low EUR 72,760 at 14:32 Lisbon).
  > Now: EUR 72,910 / $82,150.
  > Expected loss about $10 to $11.50. Balance after: about $1,039.
  > Tap Done once you've sold, or send /sold all at <price>.
  > Not financial advice.

## Workflows

| Workflow | Trigger | Notes |
|---|---|---|
| `heartbeat.yml` | `cron: "*/5 * * * *"` + `workflow_dispatch` | `concurrency: heartbeat` (cancel-in-progress: false). Commit only when state changed. GitHub's scheduler can run late under load, which is why the check uses candles since `armed_at`, not "price now" |
| `snapshot.yml` | `cron: "45 6 * * *"` + `workflow_dispatch` | Before the 07:00 UTC brief |
| `notify-alerts.yml` | `push` touching `state/alerts.json` by Claude | Sends "today's alerts" summary to Telegram |

Public repo: Actions minutes are free. Scheduled workflows get disabled after 60 days without repo activity; the daily brief commit keeps it alive.

## Daily brief (Claude Code scheduled task)

Prompt for the scheduled task, to be created at Milestone 4. Schedule it at **07:00 UTC** (08:00 Lisbon now). Portugal moves to UTC+0 on 25 Oct 2026, so from then 07:00 UTC is 07:00 Lisbon: ask Nuno before that date whether to move it to 08:00 UTC.

> Run the daily brief for the Kraken challenge in this repo. Follow CLAUDE.md and docs/strategy.md exactly. Pull first. Read state/account.json, state/alerts.json, the last 50 lines of state/inbox.jsonl and data/snapshot.json before anything else. Research news, macro calendar, ETF flows, sentiment and liquidations on the web. Write analyses/<today>-brief.md, rewrite state/alerts.json with today's plan, commit and push. Then email the brief to Nuno (address: ask the Gmail connector for the authenticated user; never write it into the repo). If data/snapshot.json is older than 3 hours, say so in the brief and do not invent prices.

Email format: see `docs/strategy.md`, "Brief format".

## Milestones

1. **Heartbeat MVP.** `src/kraken.py` (ticker, OHLC with sanity checks), `src/alerts.py` (load, evaluate, mark fired), `src/telegram.py` (send), `src/heartbeat.py`, `heartbeat.yml`. Unit tests with recorded Kraken responses, including a wick between runs and a late run. **Acceptance:** a test alert set 0.1% from price fires exactly once, and Nuno receives it on Telegram.
2. **Telegram inbound.** Polling, command parsing, buttons, `on_done`, `account.json` updates. **Acceptance:** Nuno sends "Bought 100 at <price>" in a dry-run mode and gets the right state back.
3. **Snapshot job.** Indicators from Kraken OHLC, checked against a known reference for one day.
4. **Daily brief** as a Claude Code scheduled task. First run in parallel with the old claude.ai brief for 2 days; compare.
5. **Cut-over.** Only after 1 to 4 pass: Nuno deletes his manual Kraken alerts, and the old claude.ai scheduled tasks (daily brief, event checks, weekly review) are disabled. **Until then the Kraken app alerts stay on, because there is a live position.**

Later, not now: event checks after tier-one prints (a scheduled Claude task at ~19:00 UTC on those dates), the Sunday weekly review, ETH/LINK/etc. alerts.

## Open questions for Nuno

- Brief time after 25 Oct (07:00 or 08:00 Lisbon)?
- Should watch alerts go to Telegram at all, or only into the next brief?
- ~~Quiet hours~~ Answered 2 Oct 2026: no action messages 22:30 to 06:30 Lisbon, re-check at 06:30 (see Telegram).
