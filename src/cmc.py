"""CoinMarketCap: fallback spot price only, used when Kraken can't be read."""

from __future__ import annotations

import requests

API = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
TIMEOUT = 15

# Kraken base asset -> CoinMarketCap symbol.
SYMBOLS = {"XBT": "BTC", "XDG": "DOGE"}


class CmcError(Exception):
    pass


def symbol_for(pair: str) -> str:
    base = pair[:-3]
    return SYMBOLS.get(base, base)


def quote(session: requests.Session, api_key: str, symbol: str, convert: str) -> float:
    # The free plan allows one `convert` per call.
    try:
        resp = session.get(
            API,
            params={"symbol": symbol, "convert": convert},
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()["data"][symbol]
        entry = data[0] if isinstance(data, list) else data
        return float(entry["quote"][convert]["price"])
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
        raise CmcError(f"{symbol}/{convert}: {type(exc).__name__}") from None
