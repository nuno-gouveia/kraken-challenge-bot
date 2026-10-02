import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def T(s: str) -> float:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


NOW = T("2026-10-03T12:00:40")


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status
        self.ok = status < 400

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body

    def raise_for_status(self):
        import requests

        if not self.ok:
            raise requests.HTTPError(f"{self.status_code}")


class FakeKraken:
    """Serves the fixtures the way Kraken does: OHLC rows after `since`,
    the open candle always included."""

    def __init__(self, one_min="ohlc_1m_quiet.json", fifteen_min="ohlc_15m.json", ticker="ticker.json"):
        self.one_min, self.fifteen_min, self.ticker = one_min, fifteen_min, ticker
        self.calls = []
        self.down = False

    def get(self, url, params=None, timeout=None, headers=None):
        import requests

        self.calls.append((url, dict(params or {})))
        if self.down:
            raise requests.ConnectionError("kraken down")
        path = url.rsplit("/", 1)[1]
        if path == "Ticker":
            return FakeResponse(fixture(self.ticker))
        if path == "OHLC":
            body = fixture(self.one_min if int(params["interval"]) == 1 else self.fifteen_min)
            rows = body["result"]["XXBTZEUR"]
            since = params.get("since")
            if since is not None:
                kept = [r for r in rows[:-1] if r[0] > int(since)] + rows[-1:]
                body["result"]["XXBTZEUR"] = kept
            return FakeResponse(body)
        raise AssertionError(f"unexpected GET {url}")


class FakeNotifier:
    def __init__(self, ok=True):
        self.sent = []
        self.ok = ok
        self.failed = False

    def send(self, text, silent=False):
        if not self.ok:
            self.failed = True
            return False
        self.sent.append((text, silent))
        return True


@pytest.fixture
def state(tmp_path):
    """A copy of the repo's seed state/ to run heartbeats against."""
    d = tmp_path / "state"
    shutil.copytree(ROOT / "state", d)
    return d


def read(state_dir: Path, name: str):
    return json.loads((state_dir / name).read_text())


def write(state_dir: Path, name: str, data) -> None:
    (state_dir / name).write_text(json.dumps(data, indent=2))
