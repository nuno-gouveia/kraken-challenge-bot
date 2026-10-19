"""The price-history downloader (src/history.py)."""

import gzip
import io
import zipfile
from datetime import date

from src import history
from tests.conftest import FakeResponse


def zipped(rows: list[str], header: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("k.csv", ("open_time,open,high,low,close,volume\n" if header else "") + "\n".join(rows) + "\n")
    return buf.getvalue()


def test_months_back_crosses_the_year():
    assert history.months_back(date(2026, 2, 15), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_milliseconds_and_microseconds():
    assert history.to_seconds(1_704_067_200_000) == 1_704_067_200
    assert history.to_seconds(1_735_689_600_000_000) == 1_735_689_600


def test_parse_zip_skips_a_header_row():
    data = zipped(["1704067200000,38000,38100,37900,38050,12.5,1704070799999,0,0,0,0,0"], header=True)
    assert history.parse_zip(data) == [(1704067200, "38000", "38100", "37900", "38050", "12.5")]


class FakeArchive:
    def __init__(self):
        self.urls = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        if "/monthly/" in url and "2026-09" in url:
            return FakeResponse(None, 404)
        if "/monthly/" in url:
            return type("R", (), {"status_code": 200, "content": zipped(["1754006400000,1,2,0.5,1.5,3"]),
                                  "raise_for_status": lambda self: None})()
        return type("R", (), {"status_code": 200, "content": zipped(["1759276800000,1,2,0.5,1.5,3"]),
                              "raise_for_status": lambda self: None})()


def test_update_writes_one_file_per_month_and_skips_past_months_it_has(tmp_path):
    archive = FakeArchive()
    today = date(2026, 10, 3)
    written = history.update(tmp_path, 3, archive, today=today)
    assert sorted(p.rsplit("/", 1)[1] for p in written) == ["2026-08.csv.gz"] * 4 + ["2026-10.csv.gz"] * 4  # 2026-09 is missing
    f = tmp_path / "BTCEUR" / "1h" / "2026-10.csv.gz"
    assert gzip.decompress(f.read_bytes()).decode().splitlines() == ["time,open,high,low,close,volume", "1759276800,1,2,0.5,1.5,3"]
    # the current month comes from the daily files of the days already over
    assert sum("/daily/" in u and "BTCEUR-1h" in u for u in archive.urls) == 2

    archive2 = FakeArchive()
    history.update(tmp_path, 3, archive2, today=today)
    assert not any("2026-08" in u for u in archive2.urls)  # past month already stored
