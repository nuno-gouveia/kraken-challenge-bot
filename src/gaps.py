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
        # No status filter: GitHub's status-filtered list lags by hours (on 6 Oct
        # it kept returning a run from the night, so every run sent a gap notice).
        # The plain list is current; pick the newest success from it.
        r = session.get(
            f"{API}/repos/{repo}/actions/workflows/heartbeat.yml/runs",
            params={"per_page": 100},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        r.raise_for_status()
        ends = [
            parse_ts(run["updated_at"]) for run in r.json().get("workflow_runs", [])
            if run.get("conclusion") == "success" and str(run.get("id")) != str(this_run_id)
        ]
        if ends:
            return max(ends)
        print("gaps: no successful heartbeat in the last 100 runs")
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"gaps: can't read the last heartbeat run ({type(exc).__name__})")
    return None
