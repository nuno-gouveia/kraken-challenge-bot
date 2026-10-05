# Daily brief: the procedure

A scheduled Claude Code session runs this every day at 07:00 UTC (SPEC.md milestone 4). Follow it in order. `CLAUDE.md` and `docs/strategy.md` apply throughout; read both first.

## 0. Setup

```
git checkout main && git pull --rebase origin main
pip install -q -r requirements.txt
```

**Refresh the state before reading it.** Nuno's Telegram messages wait on Telegram's side until the next heartbeat run collects them, and GitHub runs scheduled jobs late (the 06:20 snapshot has started as late as 12:23). On 5 Oct the brief told Nuno to sell half two minutes after he had reported `/sold half` on Telegram, because no heartbeat had run in between. So, with the GitHub tools (`actions_run_trigger`, workflow_dispatch on `main`):

1. Start `heartbeat.yml`, and `snapshot.yml` if `data/snapshot.json` is older than 3 hours.
2. Wait until both runs have completed (check with `actions_list`, about every 30 s, up to 10 minutes), then `git pull --rebase origin main`.
3. If a run could not be started or did not finish, say so under the data warning, and say what time the Telegram inbox is read up to.

Read `config/brief.json`. **`mode` decides where the alerts go:**

- `shadow`: write the plan to `state/alerts.proposed.json`. Do **not** touch `state/alerts.json`. The email subject starts with `[NEW SYSTEM, compare only]` and its first line says "Comparison run: act on your usual brief, not this one."
- `live`: rewrite `state/alerts.json`. The heartbeat follows it from the next run and Nuno gets a Telegram summary of the new set.

## 1. Read the state before writing a word

1. `state/account.json`: balance, cash, open positions, last confirmation.
2. `state/alerts.json`: what is armed, what fired, was done, skipped, held overnight (`held_overnight`), and any alert with `awaiting_fill: true` (Nuno tapped Done but never sent the price: ask for it in step 1 of the brief).
3. The last 50 lines of `state/inbox.jsonl`: every Telegram message since the last brief. A fill he reported is real even if nothing else mentions it. Questions or corrections he left ("saved for the next brief") get an answer in the brief. An account correction he **states** may be applied to `state/account.json` (commit it as `brief: account correction`); never infer a fill.
4. `state/heartbeat.json`: a price outage or an alerts-file problem is news for the brief.
5. `data/snapshot.json`: prices and daily indicators from Kraken. If `fetched_at` is more than 3 hours old, say so in the brief and do not invent prices. A web price may be quoted only labelled as "not Kraken".

## 2. What happened since the last brief

From the alerts and the inbox, list: alerts that fired (and whether Nuno acted), anything held overnight and how the 06:30 re-check went, fills, button presses. Put this near the top of the brief, in plain words. Read `held_overnight` exactly: an alert that still carries it and is `armed` was back on the safe side at 06:30 (no action, re-armed from 06:30); if it later shows `fired` with a `fired_at` after 06:30, that is a new touch during the day, not the overnight one. Convert every UTC time to the Lisbon date and time (00:27 Lisbon on 5 Oct is 23:27 UTC on 4 Oct).

## 3. Research

On the web: price action overnight, news, the macro calendar (what prints today after the email, and the next five days, with tier-one events marked), ETF flows, sentiment, liquidations (with their time window), open interest, and breadth across BTC, ETH, LINK, BCH, DOGE, SHIB (use the snapshot for the six).

## 4. Decide

Apply `docs/strategy.md` exactly: the verdict (up / down / don't know), the dip-setup score (which of the four steps), Plan B with both versions priced, sizing (2% risk, caps, survival check on combined exposure), hard rules for levels, tier-one dates. **Quiet hours**: an action due between 22:30 and 06:30 Lisbon is not sent until the 06:30 re-check. Say so when a level could plausibly be hit overnight.

Never change `docs/strategy.md`. Propose changes in the brief.

## 5. Write the alerts

Into `state/alerts.json` (live) or `state/alerts.proposed.json` (shadow), same schema (SPEC.md, "State files"):

- **Keep alerts whose level has not changed exactly as they are**, including `armed_at` and `status`. A new `armed_at` restarts the window the heartbeat checks, and re-arming a `fired`, `done` or `skipped` alert can make it fire again. A stable alert set is worth more than a tidy one.
- A new or moved alert gets `status: "armed"`, `armed_at` = now (UTC), a fresh id if its meaning changed.
- EUR levels rounded to the nearest EUR 50. `level_usd_ref` = level x `eur_usd` from the snapshot. Set the top-level `eur_usd`, `updated_at`, and `updated_by: "claude (daily brief)"`.
- `kind: "action"` messages start with the instruction in capitals: `SELL ALL your BTC at market now.`, `SELL HALF ...`, `BUY $420 of BTC at market now.` Set `trade` (`buy`, `sell_all`, `sell_half`). When the brief tells Nuno how to report a fill, use `/sold half at <price>` or `/sold all at <price>`; never a BTC quantity, because the bot reads a bare number as dollars. Watch messages say "Nothing to do". An alert message must be right whichever alert fires first: T2 says `SELL ALL the BTC you still hold`, never "the rest", because price can pass T1 and T2 between two checks, or T1 can fire while Nuno is asleep.
- Entries get a `guard_band` and, around a tier-one print, `valid_from`. Exits after T1 move to breakeven through `on_done` (T1 done arms the breakeven exit and disarms the original exit), never automatically.
- **Deadlines are time alerts.** Whenever an open position must be closed by a date (a tier-one print with T1 not yet done), set a time action (`direction: "time"`, `at` in UTC, `level: null`, `trade: "sell_all"`, message starting `SELL ALL your BTC at market now.`) a few hours before the print and outside quiet hours, plus a silent time watch the evening before as a heads-up. Add both ids to the `on_done.disarm` of the T1, exit and T2 alerts, and give the time action an `on_done` that disarms the position's other alerts. Keep them unchanged from brief to brief like any other alert; if the print moves, move `at`.
- Alerts that are dead, spent or withdrawn: set `status: "disabled"` with a `disabled_reason`. Drop `done`, `skipped` and `disabled` alerts older than 7 days.
- No em dash anywhere.

Then validate, and fix every ERROR before going on:

```
python -m src.validate_alerts state/alerts.json        # or state/alerts.proposed.json
```

## 6. Write the brief

`analyses/YYYY-MM-DD-brief.md` (today's UTC date), **exactly in the format and within the length limits of `docs/brief-format.md`** (the old brief's layout, made shorter: at most 450 words on a busy day). The ALERTS section lists every live alert with its level in EUR and USD and what it will tell Nuno, plus what was removed and why. Every price in EUR and USD, with the EUR/USD rate. Lisbon times. No em dash. Ends with "Not financial advice." Before committing, count the words (`wc -w`) and cut until it fits.

## 7. Commit and push to main

```
git add state/ analyses/
git commit -m "brief: YYYY-MM-DD <verdict>"
git pull --rebase origin main && git push origin HEAD:main
```

If the push is rejected, pull with rebase and push again (the heartbeat commits every few minutes). If the rebase stops on a conflict in `state/` files, the heartbeat changed them after you read them: `git rebase --abort`, copy your brief file somewhere safe, `git reset --hard origin/main`, re-read `state/alerts.json` and `state/account.json`, re-apply your plan on top of the newer statuses (never drop a `fired`, `done`, `skipped` or `held` status, or a fill, the heartbeat wrote), validate, put the brief back, commit and push again.

If you cannot push at all, still send the email, and say at the top that the alerts were NOT updated.

## 7b. Last check before sending

Telegram reports can arrive while you write. Right before the email, start `heartbeat.yml` again, wait for it, and `git pull --rebase origin main`. If `state/inbox.jsonl`, `state/account.json` or `state/alerts.json` changed since you read them, re-read them and fix every part of the brief they touch (step 1, the account, the alerts table), commit as `brief: YYYY-MM-DD updated for <what>`, then send. Never send a brief that tells Nuno to do something the state shows he has already done.

## 8. Email

With the Gmail connector, to Nuno's own address (the connected account; find it from the From header of the newest message in Sent; never write it into the repo). Subject as in `docs/brief-format.md`: `BTC brief <D Mon> - <ACTION>: <reason>` (with the shadow prefix in shadow mode). Body: the brief, HTML if the tool takes it, otherwise plain text that reads well on a phone. No em dash. Ends with "Not financial advice."
