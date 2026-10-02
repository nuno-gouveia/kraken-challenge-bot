# kraken-challenge-bot

Automation for Nuno's **Kraken Funded challenge**: $1,000 of Kraken's money, pass at **$1,120**, fail if the balance ever touches **$950**, long only, no time limit. The account has **no stop-loss orders**, so every exit is "an alert fires, Nuno sells by hand".

This repo replaces a setup where Claude wrote daily emails and Nuno typed price alerts into the Kraken app by hand. That was error prone. The new setup:

1. **A heartbeat script** (GitHub Actions, every 5 minutes) reads the Kraken price, checks it against `state/alerts.json`, and messages Nuno on **Telegram** when he has to act.
2. **Claude does the thinking once a day.** A scheduled Claude Code session writes the daily brief, sets that day's alerts by committing `state/alerts.json`, and emails the plan.
3. **Nuno reports fills back on Telegram** (`/bought`, `/sold`), and the heartbeat writes them into `state/account.json`, so every later run knows the position.

**Read `SPEC.md` for the full design and the build milestones. Read `docs/strategy.md` before writing any brief or setting any alert.**

## Build status

Milestone 1 is built and tested offline; next is Milestone 2 in `SPEC.md`. Update this section as milestones land.

| Milestone | Status |
|---|---|
| 1. Heartbeat: Kraken price + alert check + Telegram send | built (`src/`, `heartbeat.yml`, 30 tests). Acceptance pending: a live test alert reaching Nuno on Telegram |
| 2. Telegram inbound: `/bought`, `/sold`, `/status`, `/alerts` | not started |
| 3. Market snapshot job (indicators from Kraken OHLC) | not started |
| 4. Daily brief as a scheduled Claude Code task | not started |
| 5. Cut-over: retire the old claude.ai scheduled tasks | not started |

## Where things live

| Path | What | Written by |
|---|---|---|
| `state/account.json` | Balance, cash, open positions. **The single source of truth for the account.** | Heartbeat (from Telegram reports), Claude (only when Nuno states a correction) |
| `state/alerts.json` | Every live alert, its level, direction and the action text Nuno receives | Claude (daily brief), heartbeat (marks alerts fired) |
| `state/inbox.jsonl` | Every Telegram message from Nuno, appended verbatim with a timestamp | Heartbeat |
| `state/heartbeat.json` | Price-feed failure count, whether the outage message went out, alert-file problems already reported | Heartbeat |
| `data/snapshot.json` | Latest market snapshot and indicators, computed from Kraken OHLC | Snapshot job |
| `analyses/YYYY-MM-DD-brief.md` | The daily brief, as sent | Claude |
| `docs/strategy.md` | The trading rules and risk framework agreed with Nuno | Claude, only with Nuno's agreement |

## Hard rules for any Claude session in this repo

- **This repo is PUBLIC.** Never commit Nuno's email address, a Telegram chat id, a bot token, an API key or anything personal. Secrets live in GitHub Actions secrets. **Actions logs on a public repo are public too: never print a secret, a chat id or a raw Telegram payload to the log.**
- **Read the state before writing a word.** Before any brief or any alert change: read `state/account.json`, `state/alerts.json` and the tail of `state/inbox.jsonl`. A position Nuno reported on Telegram an hour ago is real even if nothing else mentions it. (In the old setup a brief told him he was in cash an hour after he had bought, because only email was checked.)
- **Prices come from Kraken.** Alerts fire on Kraken's BTC/EUR market, so Kraken's own API is the price source. CoinMarketCap is a fallback only, and a fallback reading is labelled as such.
- **Every price Nuno might act on is given in both EUR and USD.** EUR is what the alerts run on; USD is how he thinks about BTC. State the EUR/USD rate used (derive it from Kraken's XBTUSD / XBTEUR, not FX spot).
- **No em dash characters ("—") in anything Nuno reads**: Telegram messages, emails, briefs. He does not want text that reads as AI-written. Use commas, colons, full stops or parentheses.
- **Never change `docs/strategy.md` on your own.** Sizing, setups and risk limits were agreed with Nuno. Propose changes in the brief and wait for his answer.
- **Not financial advice.** Every brief and every action message ends with that note.

## Conventions

- Python 3.12, standard library plus `requests`. Keep dependencies minimal; the heartbeat must start fast.
- All timestamps in state files are UTC ISO 8601. Messages to Nuno use Lisbon time (Europe/Lisbon; UTC+1 until 25 Oct 2026, then UTC+0).
- EUR alert levels are rounded to the nearest EUR 50.
- Commits from automation use a clear prefix: `heartbeat:`, `brief:`, `snapshot:`, `telegram:`.
- Anything that writes to `state/` must `git pull --rebase` and retry on push conflict, because the heartbeat and the daily brief can both commit within minutes of each other.

## Running the heartbeat

- Tests: `pip install -r requirements-dev.txt && python -m pytest -q`. Kraken fixtures live in `tests/fixtures/` (regenerate with `python tests/fixtures/make_fixtures.py`).
- Local dry run (prints messages, writes nothing): `python -m src.heartbeat --dry-run`. Needs Kraken, which Claude's cloud sessions can't reach.
- On GitHub: Actions > heartbeat > Run workflow. `test_alert: below|above` arms a test alert 0.1% from the price (milestone 1 acceptance); `dry_run` sends nothing and commits nothing.
- An alert fires once: the heartbeat sets `status: "fired"`, `fired_at`, `fired_source` (`kraken` or `cmc`). An alert touched outside `valid_from`/`valid_until` gets one "NOT authorised now" note and `gate_notified_at`, and stays armed. An armed alert without `armed_at` is armed from the next run.
- Until Milestone 2, action messages tell Nuno to report fills in the usual chat; there are no Done/Not done buttons yet.
- Quiet hours 22:30 to 06:30 Lisbon (`src/quiet_hours.py`): action alerts hit then become `status: "held"`, nothing is sent, and the first run from 06:30 re-arms them from 06:30 and sends one "Morning update". A brief that sees `held_overnight` on an alert should say what happened overnight.

## History

The full history of the challenge (every brief since 14 Sep 2026, the long-form charter with ~46 numbered lessons) lives in Nuno's claude.ai Project "Bitcoin trading". `docs/strategy.md` is the distilled, current version of those rules. If a session has access to that Project, the newest docs there win over anything in this repo that predates them.
