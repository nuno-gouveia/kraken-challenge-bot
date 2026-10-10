"""Turn the daily brief file into the email Nuno reads, styled like the old briefs.

    python -m src.brief_email analyses/YYYY-MM-DD-brief.md --html OUT.html --text OUT.txt

Prints the subject. The brief file follows docs/brief-format.md: a "# subject"
line, ACTION and Verdict lines, then sections headed by a line in capitals.
The HTML uses inline styles only (Gmail drops <style> blocks), with the old
brief's look: a blue summary box with the action and the account, bold day
labels over numbered steps, a bordered alerts table, grey small print.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

EM_DASH = "\u2014"

BLUE, GREEN, AMBER, LINE, GREY, LIGHT = "#2b6cb0", "#38a169", "#d69e2e", "#d7dde3", "#444", "#777"
WRAP = ("font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:16px;"
        "line-height:1.5;color:#1a202c;max-width:640px")
BOX = "border-left:5px solid {};padding:14px 16px;border-radius:6px;margin:0 0 16px"
H2 = "font-size:18px;margin:22px 0 8px"
CELL = f"padding:7px 8px;border:1px solid {LINE};vertical-align:top"
SMALL = f"font-size:14.5px;color:{GREY}"

TITLES = {
    "SINCE YESTERDAY": "Since yesterday",
    "WHAT TO DO": "What to do, step by step",
    "ALERTS THE BOT IS WATCHING": "Alerts the bot is watching",
    "WHY": "Why",
    "SETUPS": "Setups",
}
SECTION = re.compile(r"^([A-Z][A-Z ]{2,})(\s*\(.*\))?$")  # "WHY", "REFERENCE LEVELS (info only)"
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
PRICE_ALERT = re.compile(r"^-\s*(below|above)\s+(EUR\s*[\d,.]+)\s*/\s*(\$[\d,.]+)\s*:\s*(.*)$", re.I)
TIME_ALERT = re.compile(r"^-\s*at\s+(.+?)\s*:\s*(.*)$", re.I)
FOOTER = ("EUR/USD", "Report fills", "Sources:", "Not financial advice")


def inline(text: str) -> str:
    """Escape, then **bold** and [label](url)."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', out)


def lead_bold(text: str) -> str:
    """Bold the first sentence, as the old briefs did on every step."""
    m = re.match(r"^(.+?[.!?])(\s+.*)?$", text)
    if not m or "**" in text:
        return inline(text)
    return f"<strong>{inline(m.group(1))}</strong>{inline(m.group(2) or '')}"


def label_bold(text: str) -> str:
    """'Price: down 1.1%' -> bold 'Price:'."""
    m = re.match(r"^([^:]{1,40}):\s+(.*)$", text)
    return f"<strong>{inline(m.group(1))}:</strong> {inline(m.group(2))}" if m else inline(text)


def parse(md: str) -> dict:
    doc = {"subject": "", "banner": [], "action": "", "verdict": "", "sections": [], "footer": []}
    current = None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# ") and not doc["subject"]:
            doc["subject"] = line[2:].strip()
        elif line.startswith(FOOTER):
            doc["footer"].append(line)
        elif line.startswith("ACTION:"):
            doc["action"] = line
        elif line.startswith("Verdict:"):
            doc["verdict"] = line
        elif SECTION.match(line):
            m = SECTION.match(line)
            current = {"name": m.group(1).strip(), "note": (m.group(2) or "").strip(), "lines": []}
            doc["sections"].append(current)
        elif current is None:
            doc["banner"].append(line)
        else:
            current["lines"].append(line)
    return doc


def account_rows(lines: list[str]) -> str:
    rows = []
    for line in lines:
        for part in re.split(r"\s+\|\s+", line):
            m = re.match(r"^([^:]{1,30}):\s*(.*)$", part)
            if m:
                key, value = m.group(1), m.group(2)
            else:
                key, _, value = part.partition(" ")
            rows.append(f'<tr><td style="padding:2px 10px 2px 0;vertical-align:top">{inline(key)}</td>'
                        f"<td><strong>{inline(value)}</strong></td></tr>")
    return f'<table style="font-size:15px;border-collapse:collapse">{"".join(rows)}</table>'


def summary_box(doc: dict, account: dict | None) -> str:
    parts = []
    m = re.match(r"^ACTION:\s*(.+?[.!?])(\s+.*)?$", doc["action"])
    if m:
        parts.append(f'<div style="font-size:19px;font-weight:700;margin-bottom:6px">ACTION: {inline(m.group(1))}</div>')
        if m.group(2):
            parts.append(f'<div style="margin-bottom:10px">{inline(m.group(2).strip())}</div>')
    elif doc["action"]:
        parts.append(f'<div style="font-size:19px;font-weight:700;margin-bottom:6px">{inline(doc["action"])}</div>')
    if doc["verdict"]:
        v = re.match(r"^(Verdict:\s*.+?[.!?])(\s+.*)?$", doc["verdict"])
        parts.append(f"<div><strong>{inline(v.group(1))}</strong>{inline(v.group(2) or '')}</div>" if v
                     else f"<div>{inline(doc['verdict'])}</div>")
    if account and account["lines"]:
        parts.append(f'<hr style="border:0;border-top:1px solid {LINE};margin:12px 0">')
        parts.append(account_rows(account["lines"]))
    return f'<div style="{BOX.format(BLUE)}">{"".join(parts)}</div>'


def steps(lines: list[str]) -> str:
    out, items, start = [], [], None

    def flush():
        nonlocal items, start
        if items:
            out.append(f'<ol start="{start}" style="margin:4px 0 12px;padding-left:22px">'
                       + "".join(f"<li>{lead_bold(i)}</li>" for i in items) + "</ol>")
        items, start = [], None

    for line in lines:
        n = NUMBERED.match(line)
        if n:
            start = start or int(n.group(1))
            items.append(n.group(2))
        else:
            flush()
            out.append(f'<p style="margin:8px 0 4px"><strong>{inline(line.lstrip("- "))}</strong></p>')
    flush()
    return "".join(out)


def alerts_table(lines: list[str]) -> str:
    rows, notes = [], []
    for line in lines:
        p, t = PRICE_ALERT.match(line), TIME_ALERT.match(line)
        if p:
            when, eur, usd, text = p.group(1).lower(), p.group(2), p.group(3), p.group(4)
            level = f"{inline(eur)} / {inline(usd)}"
        elif t:
            when, level, text = "at", inline(t.group(1)), t.group(2)
        else:
            notes.append(line)
            continue
        action = text.strip().upper().startswith(("SELL", "BUY"))
        b = (lambda s: f"<strong>{s}</strong>") if action else (lambda s: s)
        rows.append(f'<tr><td style="{CELL}">{when}</td><td style="{CELL}">{b(level)}</td>'
                    f'<td style="{CELL}">{b(inline(text))}</td></tr>')
    out = ""
    if rows:
        head = "".join(f'<th align="left" style="{CELL}">{h}</th>' for h in ("When", "EUR / USD", "What you will be told"))
        out += f'<table style="border-collapse:collapse;font-size:15px;width:100%"><tr>{head}</tr>{"".join(rows)}</table>'
    if notes:
        out += f'<p style="{SMALL}">' + "<br>".join(label_bold(n.lstrip("- ")) for n in notes) + "</p>"
    return out


def bullets(lines: list[str]) -> str:
    items = [line[2:] if line.startswith("- ") else line for line in lines]
    return ('<ul style="margin:6px 0;padding-left:22px">'
            + "".join(f'<li style="margin:3px 0">{label_bold(i)}</li>' for i in items) + "</ul>")


def footer(lines: list[str]) -> str:
    out = []
    for line in lines:
        if line.startswith("Not financial advice"):
            continue
        if line.startswith("Sources:"):
            out.append(f'<p style="font-size:13.5px;line-height:1.6;color:{GREY}"><strong>Sources:</strong>'
                       f"{inline(line[len('Sources:'):])}</p>")
        else:
            out.append(f'<p style="font-size:14px;color:#555;margin:6px 0">{label_bold(line)}</p>')
    out.append(f'<p style="font-size:13.5px;color:{LIGHT};margin-top:16px">Not financial advice.</p>')
    return "".join(out)


def to_html(md: str) -> str:
    doc = parse(md)
    sections = {s["name"]: s for s in doc["sections"]}
    body = []
    if doc["banner"]:
        body.append(f'<p style="{BOX.format(AMBER)};font-size:15px">'
                    + "<br>".join(inline(b) for b in doc["banner"]) + "</p>")
    body.append(summary_box(doc, sections.get("ACCOUNT")))
    for s in doc["sections"]:
        name = s["name"]
        if name == "ACCOUNT":
            continue
        if name == "SINCE YESTERDAY":
            body.append(f'<div style="{BOX.format(GREEN)}"><strong>Since yesterday</strong>{bullets(s["lines"])}</div>')
            continue
        if name.startswith("REFERENCE LEVELS"):
            body.append(f'<p style="{SMALL};margin-top:20px"><strong>Reference levels</strong> '
                        f'(information only, not alerts)<br>{"<br>".join(inline(x) for x in s["lines"])}</p>')
            continue
        title = TITLES.get(name, name.capitalize()) + (f" {s['note']}" if s["note"] else "")
        body.append(f'<h2 style="{H2}">{html.escape(title, quote=False)}</h2>')
        if name == "WHAT TO DO":
            body.append(steps(s["lines"]))
        elif name.startswith("ALERTS"):
            body.append(alerts_table(s["lines"]))
        else:
            body.append(bullets(s["lines"]))
    body.append(footer(doc["footer"]))
    return f'<div style="{WRAP}">' + "\n".join(body) + "</div>"


def to_text(md: str) -> str:
    """The plain-text fallback: the brief without markdown marks."""
    lines = [line for line in md.splitlines() if not line.startswith("# ")]
    text = "\n".join(lines).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1: \2", text) + "\n"


def subject(md: str) -> str:
    return parse(md)["subject"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("brief", type=Path)
    ap.add_argument("--html", type=Path, required=True)
    ap.add_argument("--text", type=Path, required=True)
    args = ap.parse_args(argv)
    md = args.brief.read_text()
    out_html, out_text = to_html(md), to_text(md)
    if EM_DASH in out_html or EM_DASH in out_text:
        print("ERROR the brief has an em dash")
        return 1
    if not parse(md)["action"]:
        print("ERROR no ACTION line: the brief does not follow docs/brief-format.md")
        return 1
    args.html.write_text(out_html)
    args.text.write_text(out_text)
    print(subject(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
