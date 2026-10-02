"""Kraken public API: ticker and OHLC, with the sanity checks from SPEC.md."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

API = "https://api.kraken.com/0/public"
TIMEOUT = 15
# The newest 1-minute candle must start within this many seconds of now.
# Kraken once served a cached OHLC window on repeat calls; a stale newest
# candle is how that shows up.
MAX_CANDLE_AGE_S = 180

# Kraken answers with its internal pair names; map the names we request.
PAIR_ALIASES = {
    "XBTEUR": "XXBTZEUR",
    "XBTUSD": "XXBTZUSD",
    "ETHEUR": "XETHZEUR",
    "ETHUSD": "XETHZUSD",
}


class KrakenError(Exception):
    pass


@dataclass(frozen=True)
class Candle:
    time: int  # unix seconds, start of the candle
    open: float
    high: float
    low: float
    close: float
    interval_s: int = 60


def _get(session: requests.Session, path: str, params: dict) -> dict:
    try:
        resp = session.get(f"{API}/{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise KrakenError(f"{path}: {type(exc).__name__}") from None
    if body.get("error"):
        raise KrakenError(f"{path}: {', '.join(body['error'])}")
    if "result" not in body:
        raise KrakenError(f"{path}: no result")
    return body["result"]


def pick(result: dict, pair: str):
    """Find the entry for `pair` in a Kraken result keyed by internal name."""
    for key in (pair, PAIR_ALIASES.get(pair)):
        if key and key in result:
            return result[key]
    candidates = [k for k in result if k != "last"]
    if len(candidates) == 1:
        return result[candidates[0]]
    raise KrakenError(f"pair {pair} missing from response")


def ticker_last(session: requests.Session, pairs: list[str]) -> dict[str, float]:
    """Last trade price for each pair, keyed by the pair name we asked for."""
    result = _get(session, "Ticker", {"pair": ",".join(pairs)})
    out = {}
    for pair in pairs:
        try:
            out[pair] = float(pick(result, pair)["c"][0])
        except (KeyError, IndexError, TypeError, ValueError):
            raise KrakenError(f"Ticker: bad entry for {pair}") from None
    return out


def parse_ohlc(result: dict, pair: str, interval_s: int) -> list[Candle]:
    try:
        rows = pick(result, pair)
        candles = [
            Candle(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), interval_s)
            for r in rows
        ]
    except (KeyError, IndexError, TypeError, ValueError):
        raise KrakenError(f"OHLC: bad rows for {pair}") from None
    return sorted(candles, key=lambda c: c.time)


def ohlc(session: requests.Session, pair: str, interval_min: int, since: int | None = None) -> list[Candle]:
    params = {"pair": pair, "interval": interval_min}
    if since is not None:
        params["since"] = since
    return parse_ohlc(_get(session, "OHLC", params), pair, interval_min * 60)


def check_fresh(candles: list[Candle], now: float, max_age_s: int = MAX_CANDLE_AGE_S) -> None:
    if not candles:
        raise KrakenError("OHLC: no candles")
    age = now - candles[-1].time
    if age > max_age_s:
        raise KrakenError(f"OHLC: newest candle is {int(age)}s old (stale response)")


@dataclass
class KrakenMarket:
    last: dict[str, float]  # pair -> last price, includes XBTEUR and XBTUSD
    candles: dict[str, list[Candle]]  # pair -> 1-minute candles (plus 15-minute fill, see below)
    eur_usd: float  # USD per EUR, implied by XBTUSD / XBTEUR


def fetch_market(
    session: requests.Session,
    pairs: list[str],
    since: dict[str, int],
    now: float,
) -> KrakenMarket:
    """One attempt: tickers for every pair plus XBTUSD, and candles per pair.

    `since[pair]` is the earliest time any armed alert on that pair needs
    candles from. Kraken serves at most 720 one-minute candles (12 hours), so
    when an alert is older than that window, 15-minute candles cover the gap
    (only those that start after the alert was armed; see alerts.py).
    """
    wanted = sorted(set(pairs) | {"XBTEUR", "XBTUSD"})
    last = ticker_last(session, wanted)
    eur_usd = last["XBTUSD"] / last["XBTEUR"]
    candles = {}
    for pair in sorted(set(pairs)):
        start = since[pair]
        minute = ohlc(session, pair, 1, since=start - 60)
        check_fresh(minute, now)
        if minute[0].time > start:
            coarse = ohlc(session, pair, 15, since=start - 900)
            minute = [c for c in coarse if c.time < minute[0].time] + minute
        candles[pair] = minute
    return KrakenMarket(last=last, candles=candles, eur_usd=eur_usd)


def fetch_market_with_retry(session, pairs, since, now_fn=time.time, sleep=time.sleep, retry_delay_s=5) -> KrakenMarket:
    try:
        return fetch_market(session, pairs, since, now_fn())
    except KrakenError as first:
        print(f"kraken: {first}; retrying in {retry_delay_s}s")
        sleep(retry_delay_s)
        return fetch_market(session, pairs, since, now_fn())
