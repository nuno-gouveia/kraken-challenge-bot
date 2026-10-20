# Event check: the procedure

A scheduled Claude Code session runs this on the evening of a tier-one US release (CPI, PCE, payrolls: 20:00 Lisbon; FOMC: about three hours after the decision), so the reaction is read, not guessed. It replaces the old claude.ai event checks (Nuno, 11 Oct 2026). The routine's prompt names the event.

It is a short evening update, not a second daily brief. `CLAUDE.md`, `docs/strategy.md` and `docs/brief-format.md` apply throughout; the mechanics are those of `docs/daily-brief.md`, referenced below by step.

## 0. Setup and fresh state

Exactly as `docs/daily-brief.md` step 0: check out `main`, start `heartbeat.yml` (and `snapshot.yml` when the snapshot is older than 3 hours), wait for both, pull. Read `config/brief.json`: `live` means this check may change `state/alerts.json`; `shadow` means it only proposes in `state/alerts.proposed.json`.

## 1. Read the state

As `docs/daily-brief.md` step 1: `state/account.json`, `state/alerts.json`, the tail of `state/inbox.jsonl`, `state/heartbeat.json`, `data/snapshot.json`, and this morning's `analyses/YYYY-MM-DD-brief.md` (what it said about tonight, and its "no new entry before" date).

## 2. Did it happen, and what did the market do?

On the web. First confirm the release actually came out today (dates move; a US government shutdown can delay BLS data). If it was postponed: say so in three lines, change nothing, send, stop.

Otherwise, briefly: the print against expectations, what it did to Fed expectations, and BTC's move since (size, levels broken or held), liquidations with their time window, and whether the move looks like exhaustion or continuation. Prices from the snapshot or the heartbeat's Kraken readings where possible; a web price is labelled "not Kraken".

## 3. Decide

Apply `docs/strategy.md` exactly, in this order:

1. **An open position comes first:** hold, or exit now. The rule for holding through the print was decided before it; the question now is only whether a level the plan depends on broke.
2. **The flash dip:** did tonight's move send a signal, or come close (the trigger is 5% under the 4-hour high)? If a signal went out, judge it: a flush (forced selling, liquidations, the rule's case) or a real break (the print changes the outlook, more selling likely). Say which, in one line; Nuno decides.
3. **No new entries from this check.** Buys come only from the flash dip. If tonight suggests pausing it (for example a shock with more to come), propose that in one line; `config/flash.json` changes only with Nuno's agreement.

## 4. Alerts

Only if step 3 changes something. Same rules as `docs/daily-brief.md` step 5: keep unchanged alerts exactly as they are, validate with `python -m src.validate_alerts`, fix every ERROR. If nothing changes, don't touch the file.

## 5. Write it

`analyses/YYYY-MM-DD-event-<event>.md` (for example `2026-10-14-event-cpi.md`), in the template of `docs/brief-format.md` with these differences:

- Subject line: `# BTC event check <D Mon> - <ACTION>: <reason in at most 8 words>`.
- **At most 250 words.** Sections: ACCOUNT, WHAT TO DO (tonight and tomorrow morning only), ALERTS THE BOT IS WATCHING (and what changed tonight), WHY (the print, the reaction, the setup: one line each). No SETUPS or REFERENCE LEVELS sections unless a level changed.
- In shadow mode, the `**Comparison run ...**` line as in the brief.

## 6. Commit, last check, email

As `docs/daily-brief.md` steps 7, 7b and 8: commit as `brief: YYYY-MM-DD event check <event>`, push with rebase, run the heartbeat again and fix the text if Nuno reported something meanwhile, then render with `python -m src.brief_email` and send `htmlBody` and `body` to Nuno's own address. Subject: the printed subject.

The next morning's brief reads this file (it is the newest thing under `analyses/`) and says what changed overnight.
