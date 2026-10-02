"""Quiet hours, 22:30 to 06:30 Lisbon (Nuno's rule, 2 Oct 2026).

An action due in that window is not sent. Nuno is assumed not to act, and the
alert is re-checked against the price at 06:30, when he gets one update.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from src.messages import LISBON

START = time(22, 30)
END = time(6, 30)


def is_quiet(ts: float) -> bool:
    t = datetime.fromtimestamp(ts, LISBON).time()
    return t >= START or t < END


def last_window(ts: float) -> tuple[float, float]:
    """Start and end of the most recent quiet window that ended at or before ts."""
    day = datetime.fromtimestamp(ts, LISBON).date()
    end = datetime.combine(day, END, LISBON)
    if end.timestamp() > ts:
        end = datetime.combine(day - timedelta(days=1), END, LISBON)
    start = datetime.combine(end.date() - timedelta(days=1), START, LISBON)
    return start.timestamp(), end.timestamp()
