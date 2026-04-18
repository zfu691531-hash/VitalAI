"""Application query object for one mental-care check-in entry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MentalCareCheckInDetailQuery:
    """Read-only query for one persisted mental-care check-in."""

    source_agent: str
    trace_id: str
    user_id: str
    checkin_id: int
