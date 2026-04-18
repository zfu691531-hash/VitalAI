"""Application query object for health alert history."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HealthAlertHistoryQuery:
    """Read-only query for recent health alerts."""

    source_agent: str
    trace_id: str
    user_id: str
    status_filter: str = ""
    limit: int = 20
