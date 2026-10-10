"""The brief file rendered as the email, in the old briefs' style."""

from src import brief_email
from tests.conftest import FIXTURES

MD = (FIXTURES / "brief_2026-10-06.md").read_text()


def test_subject_and_sections_parse():
    doc = brief_email.parse(MD)
    assert doc["subject"] == "BTC brief 6 Oct - HOLD: nothing fired, change nothing"
    assert [s["name"] for s in doc["sections"]] == [
        "ACCOUNT", "SINCE YESTERDAY", "WHAT TO DO", "ALERTS THE BOT IS WATCHING", "WHY", "SETUPS", "REFERENCE LEVELS"]
    assert doc["footer"][-1] == "Not financial advice."


def test_summary_box_has_the_action_verdict_and_account():
    out = brief_email.to_html(MD)
    assert "border-left:5px solid #2b6cb0" in out
    assert '<div style="font-size:19px;font-weight:700;margin-bottom:6px">ACTION: HOLD THE OTHER HALF.</div>' in out
    assert "<strong>Verdict: DON'T KNOW.</strong>" in out
    assert "<td><strong>$1,055.26, cash $845.26</strong></td>" in out
    assert ">Equity</td><td><strong>~$1,058.25</strong>" in out


def test_steps_alerts_and_reasons():
    out = brief_email.to_html(MD)
    assert '<p style="margin:8px 0 4px"><strong>Today (Tue 6 Oct)</strong></p>' in out
    assert '<ol start="2"' in out and "<li><strong>Hold the other half.</strong> Do not add.</li>" in out
    assert "<strong>EUR 74,600 / $83,606</strong>" in out  # an action alert row is bold
    assert ">EUR 72,150 / $80,860<" in out  # a watch row is not
    assert "<li style=\"margin:3px 0\"><strong>Price:</strong> down 1.1%" in out


def test_footer_links_escaping_and_disclaimer():
    out = brief_email.to_html(MD)
    assert '<a href="https://investinglive.com/news/' in out
    assert "/bought &lt;usd&gt; at &lt;price&gt;" in out
    assert out.endswith("Not financial advice.</p></div>")
    assert out.count("Not financial advice.") == 1
    assert "—" not in out


def test_plain_text_fallback():
    text = brief_email.to_text(MD)
    assert text.startswith("Comparison run: act on your usual brief, not this one.")
    assert "**" not in text and "Week ahead: https://investinglive.com/" in text


def test_cli_refuses_a_brief_without_an_action(tmp_path):
    brief = tmp_path / "b.md"
    brief.write_text("# BTC brief\n\nWHY\n- Price: flat\n")
    assert brief_email.main([str(brief), "--html", str(tmp_path / "o.html"), "--text", str(tmp_path / "o.txt")]) == 1
