"""The Telegram TLDR of a brief."""

import subprocess

from src import tldr
from tests.conftest import FIXTURES
from tests.test_heartbeat import assert_telegram_html

MD = (FIXTURES / "brief_2026-10-06.md").read_text()


def test_tldr_has_the_action_position_steps_and_alerts():
    text = tldr.message(MD)
    assert_telegram_html(text)
    assert text.startswith("<b>TLDR: Brief 6 Oct - HOLD: nothing fired, change nothing</b>\n")
    assert "<b>ACTION: HOLD THE OTHER HALF. Buy nothing, change nothing.</b>" in text
    assert "Position: 0.0024980 BTC (half), cost $210 at $84,065" in text
    assert "\n1. Hold the other half. Do not add.\n" in text
    assert "Alerts: 3 watched, 2 that ask you to act" in text
    assert text.endswith("Full version in your email.\nNot financial advice.")
    assert "—" not in text
    assert len(text) < 1200  # a TLDR, not the brief


def test_shadow_prefix_dropped_and_update_marked():
    md = MD.replace("# BTC brief", "# [NEW SYSTEM, compare only] BTC brief")
    assert tldr.message(md, updated=True).startswith("<b>TLDR: Brief 6 Oct - HOLD: nothing fired, change nothing</b> (updated)")


def test_no_alerts_and_long_step_lists():
    md = MD.split("ALERTS THE BOT IS WATCHING")[0] + "ALERTS THE BOT IS WATCHING\n- None armed.\n"
    md = md.replace("3. Nothing to do", "3. Step three.\n4. Step four.\n5. Nothing to do")
    text = tldr.message(md)
    assert "Alerts: none watched." in text and "(+2 more in the email)" in text


def test_changed_files_picks_only_briefs_and_event_checks(tmp_path, monkeypatch):
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
    (tmp_path / "analyses").mkdir()
    (tmp_path / "analyses/2026-10-11-brief.md").write_text("a")
    run("add", "-A"); run("commit", "-qm", "one")
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    (tmp_path / "analyses/2026-10-11-brief.md").write_text("b")
    (tmp_path / "analyses/2026-10-14-event-cpi.md").write_text("c")
    (tmp_path / "analyses/notes.md").write_text("d")
    run("add", "-A"); run("commit", "-qm", "two")
    monkeypatch.chdir(tmp_path)
    assert sorted(tldr.changed_files(before, "HEAD")) == [
        ("A", "analyses/2026-10-14-event-cpi.md"), ("M", "analyses/2026-10-11-brief.md")]
