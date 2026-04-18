"""Application query object for one daily-life check-in entry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DailyLifeCheckInDetailQuery:
    """Read-only query for one persisted daily-life check-in."""

    source_agent: str
    trace_id: str
    user_id: str
    checkin_id: int
