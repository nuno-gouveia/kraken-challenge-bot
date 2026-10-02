"""Telegram Bot API: outbound messages.

The bot token is part of every request URL, and requests puts the URL into
its exception text. So no requests exception is ever re-raised or printed
from here: errors are rebuilt from the exception type and Telegram's own
description only. Never log the chat id or a raw payload either.
"""

from __future__ import annotations

import time

import requests

API = "https://api.telegram.org"
TIMEOUT = 15


class TelegramError(Exception):
    pass


def send_message(
    session: requests.Session,
    token: str,
    chat_id: str,
    text: str,
    silent: bool = False,
    reply_markup: dict | None = None,
    sleep=time.sleep,
) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": silent,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    wait = 0
    for _ in range(2):
        sleep(wait)
        wait = 2
        try:
            resp = session.post(f"{API}/bot{token}/sendMessage", json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            error = f"sendMessage: {type(exc).__name__}"
            continue
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.ok and body.get("ok"):
            return
        error = f"sendMessage: HTTP {resp.status_code} {body.get('description', '')}".strip()
        if resp.status_code != 429 and resp.status_code < 500:
            raise TelegramError(error)
        wait = min(int((body.get("parameters") or {}).get("retry_after", 2)), 10)
    raise TelegramError(error)
