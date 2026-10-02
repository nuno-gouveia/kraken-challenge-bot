"""Apply Nuno's reported fills to state/account.json.

Balance is on a cost basis (as in the seed file): buying moves cash into a
position at cost and leaves the balance alone; selling turns the position
back into cash and adds the realised result to the balance. Fees are not
modelled; Nuno reports the price he got.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

DUST_USD = 0.5  # a position worth less than this at cost is treated as closed


@dataclass
class Fill:
    account: dict  # the account after the fill (a copy; the input is untouched)
    asset: str
    side: str  # "buy" or "sell"
    usd: float  # spent (buy) or received (sell)
    qty: float
    price_usd: float
    realised_usd: float = 0.0
    closed: bool = False  # the sell closed the whole position
    warnings: list[str] = field(default_factory=list)


def qty_key(asset: str) -> str:
    return f"qty_{asset.lower()}"


def position(account: dict, asset: str) -> dict | None:
    return next((p for p in account.get("positions", []) if p.get("asset") == asset and p.get("side", "long") == "long"), None)


def qty_of(pos: dict) -> float:
    return float(pos.get("qty", pos.get(qty_key(pos["asset"]), 0.0)))


def _next_trade_id(account: dict) -> str:
    ids = [t.get("id", "") for t in account.get("positions", []) + account.get("closed_trades", [])]
    nums = [int(i.split("-")[1]) for i in ids if i.startswith("trade-") and i.split("-")[1].isdigit()]
    return f"trade-{max(nums, default=0) + 1}"


def _stamp(acc: dict, now_iso: str, text: str) -> None:
    acc["last_confirmed_at"] = now_iso
    acc["last_confirmed_via"] = "telegram"
    acc["last_confirmed_text"] = text


def buy(account: dict, asset: str, usd: float, price_usd: float, now_iso: str, text: str,
        price_eur: float | None = None) -> Fill:
    acc = copy.deepcopy(account)
    warnings = []
    cash = float(acc.get("cash_usd", 0.0))
    if usd > cash + 0.01:
        warnings.append(f"That is more than the cash on record (${cash:,.2f}). Recorded anyway; check it.")
    qty = usd / price_usd
    pos = position(acc, asset)
    if pos:
        new_qty = qty_of(pos) + qty
        pos["size_usd"] = round(float(pos["size_usd"]) + usd, 2)
        pos["entry_usd"] = round(pos["size_usd"] / new_qty, 2)
        pos[qty_key(asset)] = round(new_qty, 8)
        pos.pop("qty", None)
        pos.setdefault("adds", []).append({"at": now_iso, "usd": usd, "price_usd": price_usd})
    else:
        pos = {
            "id": _next_trade_id(acc),
            "asset": asset,
            "side": "long",
            "size_usd": round(usd, 2),
            "entry_usd": price_usd,
            qty_key(asset): round(qty, 8),
            "opened_at": now_iso,
        }
        if price_eur:
            pos["entry_eur_approx"] = round(price_eur)
        acc.setdefault("positions", []).append(pos)
    acc["cash_usd"] = round(cash - usd, 2)
    _stamp(acc, now_iso, text)
    return Fill(acc, asset, "buy", usd, qty, price_usd, warnings=warnings)


def sell(account: dict, asset: str, amount, price_usd: float, now_iso: str, text: str) -> Fill:
    """amount: "all", "half", or a USD value to sell."""
    acc = copy.deepcopy(account)
    pos = position(acc, asset)
    if pos is None:
        raise ValueError(f"no open {asset} position on record")
    held = qty_of(pos)
    if amount == "all":
        qty = held
    elif amount == "half":
        qty = held / 2
    else:
        qty = min(float(amount) / price_usd, held)
    proceeds = qty * price_usd
    cost = float(pos["size_usd"]) * qty / held
    realised = proceeds - cost
    left_qty = held - qty
    left_size = float(pos["size_usd"]) - cost
    closed = left_size < DUST_USD

    acc["cash_usd"] = round(float(acc.get("cash_usd", 0.0)) + proceeds, 2)
    acc["balance_usd"] = round(float(acc.get("balance_usd", 0.0)) + realised, 2)
    pos.setdefault("sells", []).append(
        {"at": now_iso, "qty": round(qty, 8), "price_usd": price_usd,
         "cost_usd": round(cost, 2), "realised_usd": round(realised, 2)}
    )
    if closed:
        acc["positions"].remove(pos)
        total = sum(s["realised_usd"] for s in pos["sells"])
        acc.setdefault("closed_trades", []).append({
            "id": pos.get("id"),
            "asset": asset,
            "size_usd": round(sum(s["cost_usd"] for s in pos["sells"]), 2),
            "opened_at": pos.get("opened_at"),
            "closed_at": now_iso,
            "result_usd": round(total, 2),
        })
    else:
        pos["size_usd"] = round(left_size, 2)
        pos[qty_key(asset)] = round(left_qty, 8)
        pos.pop("qty", None)
    _stamp(acc, now_iso, text)
    return Fill(acc, asset, "sell", proceeds, qty, price_usd, realised_usd=realised, closed=closed)
