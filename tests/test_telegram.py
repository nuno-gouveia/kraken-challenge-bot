import pytest
import requests

from src import telegram
from tests.conftest import FakeResponse

TOKEN = "123456:SECRET-TOKEN"


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_sends_html_and_silent_flag():
    s = Session(FakeResponse({"ok": True}))
    telegram.send_message(s, TOKEN, "42", "<b>hi</b>", silent=True, sleep=lambda _: None)
    _, payload = s.posts[0]
    assert payload["parse_mode"] == "HTML"
    assert payload["disable_notification"] is True


def test_errors_never_carry_the_token():
    # requests puts the full URL, token included, into its exception text.
    boom = requests.ConnectionError(f"Max retries exceeded with url: /bot{TOKEN}/sendMessage")
    s = Session(boom, boom)
    with pytest.raises(telegram.TelegramError) as exc:
        telegram.send_message(s, TOKEN, "42", "x", sleep=lambda _: None)
    assert TOKEN not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__context__ is None


def test_retries_once_on_rate_limit_then_succeeds():
    waits = []
    s = Session(
        FakeResponse({"ok": False, "description": "Too Many Requests", "parameters": {"retry_after": 3}}, 429),
        FakeResponse({"ok": True}),
    )
    telegram.send_message(s, TOKEN, "42", "x", sleep=waits.append)
    assert waits == [0, 3]


def test_bad_request_is_not_retried():
    s = Session(FakeResponse({"ok": False, "description": "Bad Request: chat not found"}, 400))
    with pytest.raises(telegram.TelegramError, match="chat not found"):
        telegram.send_message(s, TOKEN, "42", "x", sleep=lambda _: None)
    assert len(s.posts) == 1
