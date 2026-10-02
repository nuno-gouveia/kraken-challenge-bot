"""Price source for the heartbeat: Kraken, then CoinMarketCap as a labelled fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from src import cmc, kraken
from src.kraken import Candle


class NoPrices(Exception):
    pass


@dataclass
class Prices:
    source: str  # "kraken" or "cmc"
    last: dict[str, float]  # pair -> last price in the pair's quote currency
    candles: dict[str, list[Candle]]  # pair -> candles to check alerts against
    eur_usd: float  # USD per EUR


def from_cmc(session: requests.Session, api_key: str, pairs: list[str], now: float) -> Prices:
    """Spot prices only. Each pair gets one synthetic candle at the current
    price, so alerts can still fire, but a wick between runs is invisible."""
    btc_eur = cmc.quote(session, api_key, "BTC", "EUR")
    btc_usd = cmc.quote(session, api_key, "BTC", "USD")
    last = {"XBTEUR": btc_eur, "XBTUSD": btc_usd}
    for pair in pairs:
        if pair not in last:
            last[pair] = cmc.quote(session, api_key, cmc.symbol_for(pair), pair[-3:])
    minute = int(now) - int(now) % 60
    candles = {p: [Candle(minute, last[p], last[p], last[p], last[p])] for p in pairs}
    return Prices("cmc", last, candles, btc_usd / btc_eur)


def fetch(
    session: requests.Session,
    since: dict[str, int],
    cmc_key: str | None,
    now_fn=time.time,
    sleep=time.sleep,
) -> Prices:
    pairs = sorted(since)
    try:
        m = kraken.fetch_market_with_retry(session, pairs, since, now_fn=now_fn, sleep=sleep)
        return Prices("kraken", m.last, m.candles, m.eur_usd)
    except kraken.KrakenError as exc:
        print(f"kraken: {exc}; giving up on Kraken for this run")
    if not cmc_key:
        raise NoPrices("Kraken failed and no CMC_API_KEY is set")
    try:
        return from_cmc(session, cmc_key, pairs, now_fn())
    except cmc.CmcError as exc:
        raise NoPrices(f"Kraken and CoinMarketCap both failed ({exc})") from None
