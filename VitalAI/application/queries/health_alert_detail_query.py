"""Application query object for one health alert entry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HealthAlertDetailQuery:
    """Read-only query for one persisted health alert."""

    source_agent: str
    trace_id: str
    user_id: str
    alert_id: int
