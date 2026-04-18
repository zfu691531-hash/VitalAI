"""Application command object for health alert status transitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HealthAlertStatusUpdateCommand:
    """Mutating command for one persisted health alert entry."""

    source_agent: str
    trace_id: str
    user_id: str
    alert_id: int
    target_status: str
