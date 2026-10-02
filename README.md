# kraken-challenge-bot

A price-alert heartbeat and Telegram bot for a Kraken Funded challenge, with a daily plan written by Claude.

- Every 5 minutes a GitHub Action reads the Kraken BTC/EUR price and checks it against `state/alerts.json`.
- When an alert fires, a Telegram message says exactly what to do.
- Once a day, Claude analyses the market, sets the alerts and emails the plan.

Design and build plan: [`SPEC.md`](SPEC.md). Trading rules: [`docs/strategy.md`](docs/strategy.md). Instructions for Claude Code sessions: [`CLAUDE.md`](CLAUDE.md).

Not financial advice.
