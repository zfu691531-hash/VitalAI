"""Application query object for daily-life check-in history."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DailyLifeCheckInHistoryQuery:
    """Read-only query for recent daily-life check-ins."""

    source_agent: str
    trace_id: str
    user_id: str
    urgency_filter: str = ""
    limit: int = 20
