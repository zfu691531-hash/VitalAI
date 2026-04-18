"""Application query object for mental-care check-in history."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MentalCareCheckInHistoryQuery:
    """Read-only query for recent mental-care check-ins."""

    source_agent: str
    trace_id: str
    user_id: str
    mood_filter: str = ""
    limit: int = 20
