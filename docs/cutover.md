# Milestone 5: cut-over checklist

Nothing here is automatic. Each step is Nuno's call. Until the last box is ticked, **the Kraken app alerts stay on**, because there is a live position.

## Prove each milestone

- [ ] **1. Heartbeat.** A test alert 0.1% from the price reached Telegram once and never again (Actions > heartbeat > Run workflow, `test_alert: below`).
- [ ] **1b. Schedule.** Actions > heartbeat shows `schedule` runs roughly every 5 to 15 minutes for a full day, all green.
- [ ] **2. Telegram inbound.** In the bot chat: `/dryrun Bought 100 at <price>` answers with the right state and changes nothing; `/status`, `/alerts`, `/price` answer within a run or two.
- [ ] **3. Snapshot.** Actions > snapshot ran (or Run workflow by hand) and `data/snapshot.json` exists. Check one day's numbers against a chart: BTC/USD daily RSI14 and EMA200 on Kraken or TradingView (daily, UTC candles) within a few tenths.
- [ ] **4. Daily brief, shadow.** Two mornings of `[NEW SYSTEM, compare only]` emails next to the usual brief. Compare verdict, levels and the account section.

## Switch over

- [ ] Set `config/brief.json` `mode` to `live` (any Claude session can do it on request; commit `brief: go live`). From the next brief, `state/alerts.json` is Claude's daily plan and Telegram follows it.
- [ ] The first live brief's alerts arrive on Telegram ("Today's alerts are set"). Check them against the email once.
- [ ] Delete the manual price alerts in the Kraken app.
- [ ] Disable the old claude.ai scheduled tasks: daily brief, event checks, weekly review.
- [ ] Update the build-status table in `CLAUDE.md`.

## Rolling back

Set `mode` back to `shadow`, put the Kraken app alerts back, re-enable the old daily brief. The heartbeat keeps watching whatever is in `state/alerts.json`; disable the heartbeat workflow (Actions > heartbeat > ... > Disable) to stop it entirely.
