"""Telegram message text. Short, the action first, both currencies, Lisbon time.

No em dash characters anywhere in this file's output (Nuno's rule).
"""

from __future__ import annotations

from datetime import datetime
from html import escape as _escape
from zoneinfo import ZoneInfo

from src.alerts import Hit, parse_ts
from src.kraken import Candle

LISBON = ZoneInfo("Europe/Lisbon")


def escape(text: str) -> str:
    # Telegram HTML only needs <, > and &; leave apostrophes readable.
    return _escape(text, quote=False)

NFA = "Not financial advice."
# Milestone 2 replaces this with the Done / Not done buttons and /sold.
CONFIRM_HINT = "Once you've acted, report it in the usual chat with Claude (replies to this bot are not wired up yet)."
SLIPPAGE = 0.003  # docs/strategy.md: assume 0.3% on an exit
LATE_AFTER_S = 600

ASSETS = {"XBT": "BTC", "XDG": "DOGE"}


def asset(pair: str) -> str:
    base = pair[:-3]
    return ASSETS.get(base, base)


def num(x: float) -> str:
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    if abs(x) >= 1:
        return f"{x:,.2f}"
    return f"{x:.6g}"


def money(x: float, ccy: str) -> str:
    return f"${num(x)}" if ccy == "USD" else f"{ccy} {num(x)}"


def both(x: float, quote: str, eur_usd: float) -> str:
    """A price in the pair's quote currency, plus the other one."""
    if quote == "EUR":
        return f"EUR {num(x)} / ${num(x * eur_usd)}"
    if quote == "USD":
        return f"${num(x)} / EUR {num(x / eur_usd)}"
    return money(x, quote)


def signed_usd(x: float) -> str:
    return f"{'-' if x < 0 else '+'}${abs(x):,.2f}"


def lisbon(ts: float, now: float) -> str:
    dt = datetime.fromtimestamp(ts, LISBON)
    if dt.date() == datetime.fromtimestamp(now, LISBON).date():
        return f"{dt:%H:%M}"
    return f"{dt.day} {dt:%b %H:%M}"


def when(c: Candle, now: float) -> str:
    if c.interval_s <= 60:
        return lisbon(c.time, now)
    return f"{lisbon(c.time, now)} to {lisbon(c.time + c.interval_s, now)}"


def source_note(prices) -> str:
    rate = f"EUR/USD {prices.eur_usd:.4f}"
    if prices.source == "kraken":
        return f"Kraken, {rate} from XBTUSD/XBTEUR"
    return f"FALLBACK price from CoinMarketCap, not Kraken; {rate}"


def usd_price(prices, pair: str) -> float:
    quote = pair[-3:]
    last = prices.last[pair]
    return last * prices.eur_usd if quote == "EUR" else last


def position_lines(account: dict | None, name: str, usd_now: float) -> list[str]:
    lines = []
    for pos in (account or {}).get("positions", []):
        if pos.get("asset") != name or pos.get("side", "long") != "long":
            continue
        try:
            qty = float(pos.get("qty", pos.get(f"qty_{name.lower()}")))
            size = float(pos["size_usd"])
        except (KeyError, TypeError, ValueError):
            continue
        value = qty * usd_now
        after_slip = value * (1 - SLIPPAGE) - size
        lines.append(
            f"Your {name}: {qty:g} bought for ${size:,.2f}, worth about ${value:,.2f} now ({signed_usd(value - size)})."
        )
        balance = account.get("balance_usd")
        if isinstance(balance, (int, float)):
            lines.append(
                f"If you sell all now: about {signed_usd(after_slip)} after 0.3% slippage, "
                f"balance about ${balance + after_slip:,.2f}."
            )
    return lines


def alert_message(hit: Hit, prices, account: dict | None, now: float, overnight_at: float | None = None) -> str:
    a = hit.alert
    pair, quote, name = a["pair"], a["pair"][-3:], asset(a["pair"])
    rate = prices.eur_usd
    action = a["kind"] == "action"
    below = a["direction"] == "below"

    lines = [f"<b>ACTION: {escape(a['message'])}</b>" if action else f"<b>{escape(a['message'])}</b>"]
    touched = (
        f"{name}/{quote} touched {both(a['level'], quote, rate)} at {when(hit.first_touch, now)} Lisbon"
    )
    if prices.source == "kraken":
        touched += f"; {'low' if below else 'high'} since then {money(hit.extreme, quote)}"
    lines.append(f"{touched}. (Alert {escape(a['id'])})")
    if overnight_at is not None:
        lines.append(
            f"Held overnight: first touched at {lisbon(overnight_at, now)} (quiet hours), "
            "and still through the level at the 06:30 re-check."
        )
    lines.append(f"Now: {both(prices.last[pair], quote, rate)} ({source_note(prices)}).")

    band = a.get("guard_band")
    if band:
        low, high = band
        lines.append(
            f"Only buy if Kraken shows between {money(low, quote)} and {money(high, quote)} "
            f"(${num(low * rate)} to ${num(high * rate)}). Below {money(low, quote)} do NOT buy."
        )
        if not low <= prices.last[pair] <= high:
            lines.append("Right now the price is OUTSIDE that band: do NOT buy.")

    late_s = now - (hit.first_touch.time + hit.first_touch.interval_s)
    if late_s > LATE_AFTER_S:
        late = f"Note: the level was first touched about {int((now - hit.first_touch.time) // 60)} min ago (this check ran late)."
        if action and not band:
            late += " Act at market on sight, do not wait for the level to come back."
        lines.append(late)

    if action:
        lines.extend(position_lines(account, name, usd_price(prices, pair)))
        lines.append(CONFIRM_HINT)
    lines.append(NFA)
    return "\n".join(lines)


def gate_message(hit: Hit, prices, now: float) -> str:
    a = hit.alert
    pair, quote = a["pair"], a["pair"][-3:]
    vf, vu = parse_ts(a.get("valid_from")), parse_ts(a.get("valid_until"))
    window = " ".join(
        part for part in (
            f"from {lisbon(vf, now)}" if vf else "",
            f"until {lisbon(vu, now)}" if vu else "",
        ) if part
    )
    return "\n".join([
        "<b>Level touched, but NOT authorised now. Do nothing.</b>",
        f"{asset(pair)}/{quote} touched {both(a['level'], quote, prices.eur_usd)} at {when(hit.first_touch, now)} Lisbon "
        f"(alert {escape(a['id'])}: {escape(a['message'])})",
        f"This alert only counts {window} Lisbon time. It stays armed and fires if the level is touched inside that window.",
        f"Now: {both(prices.last[pair], quote, prices.eur_usd)} ({source_note(prices)}).",
        NFA,
    ])


def morning_message(entries: list[tuple[dict, float, float, bool]], prices, now: float) -> str:
    """One update at 06:30 for actions held overnight.

    entries: (alert, first touch time, overnight extreme, still through the level now)
    """
    lines = [
        "<b>Morning update: actions held overnight (quiet hours 22:30 to 06:30 Lisbon).</b>",
        "I assumed you did nothing overnight, and re-checked each one at 06:30:",
    ]
    for a, first_at, extreme, still in entries:
        quote = a["pair"][-3:]
        below = a["direction"] == "below"
        lines.append("")
        lines.append(f"<b>{escape(a['message'])}</b> (alert {escape(a['id'])})")
        lines.append(
            f"Level {both(a['level'], quote, prices.eur_usd)}, first touched at {lisbon(first_at, now)}; "
            f"{'low' if below else 'high'} overnight {money(extreme, quote)}."
        )
        if still:
            lines.append(f"Still {'below' if below else 'above'} the level: <b>the action stands</b>, see the next message.")
        else:
            lines.append(
                f"Back {'above' if below else 'below'} the level now: no action. "
                "The alert is armed again from 06:30 and fires if the level is touched again."
            )
    lines += [
        "",
        f"Now: {both(prices.last[entries[0][0]['pair']], entries[0][0]['pair'][-3:], prices.eur_usd)} ({source_note(prices)}).",
        "Today's brief re-plans the day.",
        NFA,
    ]
    return "\n".join(lines)


def outage_message(failures: int) -> str:
    return "\n".join([
        "<b>I can't read prices right now, your alerts are NOT being watched.</b>",
        f"Kraken and the fallback have both failed {failures} checks in a row. "
        "Keep your Kraken app alerts on. I'll message you when I'm back.",
    ])


def recovered_message(prices) -> str:
    return f"<b>Back online.</b> Prices are being read again ({source_note(prices)}) and your alerts are being watched."


def problems_message(problems: list[str]) -> str:
    listed = "\n".join(f"- {escape(p)}" for p in problems)
    return "\n".join([
        "<b>Problem with the alerts file: these alerts are NOT being watched until it's fixed.</b>",
        listed,
        "Claude fixes this in the next brief; keep your Kraken app alerts on meanwhile.",
    ])


def problems_cleared_message() -> str:
    return "<b>The alerts file is fixed.</b> All armed alerts are being watched again."
