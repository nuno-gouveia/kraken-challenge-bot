"""When did the heartbeat last run? GitHub sometimes doesn't start it at all
(5 Oct 2026, 20:35 to 21:20 Lisbon: jobs queued, never ran, no logs), and a
run that never starts can't say so. So each run asks GitHub when the last
successful heartbeat finished, and the first run after a gap tells Nuno.

Asking GitHub, rather than writing a timestamp to state/, keeps the heartbeat
from committing every five minutes.
"""

from __future__ import annotations

import requests

from src.alerts import parse_ts

GAP_AFTER_S = 15 * 60  # three missed runs
API = "https://api.github.com"


def last_success_end(session: requests.Session, repo: str, token: str, this_run_id: str | None) -> float | None:
    """When the latest successful heartbeat run (other than this one) finished, or None if unknown."""
    try:
        r = session.get(
            f"{API}/repos/{repo}/actions/workflows/heartbeat.yml/runs",
            params={"status": "success", "per_page": 5},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        r.raise_for_status()
        for run in r.json().get("workflow_runs", []):
            if str(run.get("id")) != str(this_run_id):
                return parse_ts(run["updated_at"])
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"gaps: can't read the last heartbeat run ({type(exc).__name__})")
    return None
