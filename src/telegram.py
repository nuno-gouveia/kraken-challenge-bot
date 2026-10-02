"""Telegram Bot API: send messages, read updates, answer button presses.

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


def call(session: requests.Session, token: str, method: str, payload: dict, sleep=time.sleep):
    """POST one Bot API method; retry once on a network error, 429 or 5xx."""
    wait = 0
    for _ in range(2):
        sleep(wait)
        wait = 2
        try:
            resp = session.post(f"{API}/bot{token}/{method}", json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            error = f"{method}: {type(exc).__name__}"
            continue
        try:
            body = resp.json()
        except ValueError:
            body = {}
        if resp.ok and body.get("ok"):
            return body.get("result")
        error = f"{method}: HTTP {resp.status_code} {body.get('description', '')}".strip()
        if resp.status_code != 429 and resp.status_code < 500:
            raise TelegramError(error)
        wait = min(int((body.get("parameters") or {}).get("retry_after", 2)), 10)
    raise TelegramError(error)


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
    call(session, token, "sendMessage", payload, sleep=sleep)


def get_updates(session: requests.Session, token: str, offset: int | None, sleep=time.sleep) -> list[dict]:
    """Pending messages and button presses. Passing `offset` confirms (and
    so deletes on Telegram's side) every update below it."""
    payload = {"timeout": 0, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    return call(session, token, "getUpdates", payload, sleep=sleep) or []


def answer_callback(session: requests.Session, token: str, callback_id: str, text: str, sleep=time.sleep) -> None:
    call(session, token, "answerCallbackQuery", {"callback_query_id": callback_id, "text": text}, sleep=sleep)


def remove_buttons(session: requests.Session, token: str, chat_id, message_id: int, sleep=time.sleep) -> None:
    call(session, token, "editMessageReplyMarkup",
         {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}}, sleep=sleep)
