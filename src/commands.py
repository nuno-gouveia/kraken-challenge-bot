"""Parse what Nuno sends the bot: slash commands or plain text.

    /bought 420 at 84065          Bought 420$ at 84065$       bought 100 eth at 2510
    /sold all at 82150            sold half at 86,800         sold 200 at 86800
    /status  /alerts  /price  /help
    /dryrun <any of the above>    shows the result, changes nothing

Prices are USD unless marked EUR ("at 74600 EUR", "at €74600").
"""

from __future__ import annotations

import re

ASSETS = {"btc": "BTC", "xbt": "BTC", "bitcoin": "BTC", "eth": "ETH", "link": "LINK",
          "bch": "BCH", "doge": "DOGE", "xdg": "DOGE", "shib": "SHIB"}

_CUR = r"(?:\$|usd|€|eur|euros?|dollars?)"
_NUM = r"\d[\d,]*(?:\.\d+)?"
_PRICE = rf"(?:at|@)\s*(?P<pcur1>{_CUR})?\s*(?P<price>{_NUM})\s*(?P<pcur2>{_CUR})?"
_ASSET = r"(?:of\s+)?(?P<asset>[a-z]+)?"

BUY = re.compile(rf"^(?:bought|buy)\s+\$?\s*(?P<usd>{_NUM})\s*(?:\$|usd|dollars?)?\s*{_ASSET}\s*{_PRICE}\s*(?P<asset2>[a-z]+)?$", re.I)
SELL = re.compile(
    rf"^(?:sold|sell)\s+(?:(?P<word>all|everything|half|the\s+rest|rest)|\$?\s*(?P<usd>{_NUM})\s*(?:\$|usd|dollars?)?)"
    rf"\s*{_ASSET}\s*{_PRICE}\s*(?P<asset2>[a-z]+)?$",
    re.I,
)
SIMPLE = {"status": "status", "alerts": "alerts", "price": "price", "help": "help", "start": "help"}


def _number(s: str) -> float:
    return float(s.replace(",", ""))


def _asset(m: re.Match) -> str | None:
    """BTC unless an asset is named; None if the name isn't one we trade."""
    names = [n for n in (m.group("asset"), m.group("asset2")) if n]
    if not names:
        return "BTC"
    return ASSETS.get(names[0].lower())


def _price_ccy(m: re.Match) -> str:
    marks = " ".join(filter(None, (m.group("pcur1"), m.group("pcur2")))).lower()
    return "EUR" if ("€" in marks or "eur" in marks) else "USD"


def parse(text: str) -> dict:
    raw = (text or "").strip()
    dry = False
    m = re.match(r"^/dry[\s_-]?run(?:@\w+)?\s*(.*)$", raw, re.I | re.S)
    if m:
        dry, raw = True, m.group(1).strip()
    body = re.sub(r"^/(\w+)(?:@\w+)?", r"\1", raw).strip().rstrip(".!")
    body = re.sub(r"\s+", " ", body)
    out: dict = {"dry": dry}

    word = body.lower()
    if word in SIMPLE:
        return {**out, "cmd": SIMPLE[word]}

    if m := BUY.match(body):
        asset = _asset(m)
        if asset is None:
            return {**out, "cmd": "unknown", "why": "unknown asset"}
        return {**out, "cmd": "bought", "asset": asset, "usd": _number(m.group("usd")),
                "price": _number(m.group("price")), "price_ccy": _price_ccy(m)}

    if m := SELL.match(body):
        asset = _asset(m)
        if asset is None:
            return {**out, "cmd": "unknown", "why": "unknown asset"}
        w = (m.group("word") or "").lower()
        amount: str | float = "half" if w == "half" else "all" if w else _number(m.group("usd"))
        return {**out, "cmd": "sold", "asset": asset, "amount": amount,
                "price": _number(m.group("price")), "price_ccy": _price_ccy(m)}

    return {**out, "cmd": "unknown"}
