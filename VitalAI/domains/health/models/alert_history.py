"""Health alert history read models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class HealthAlertEntry:
    """One persisted health alert entry."""

    user_id: str
    risk_level: str
    source_agent: str
    trace_id: str
    message_id: str
    created_at: str


@dataclass(slots=True)
class HealthAlertSnapshot:
    """A read-model snapshot of recent health alerts for one user."""

    user_id: str
    entries: list[HealthAlertEntry] = field(default_factory=list)

    @property
    def alert_count(self) -> int:
        """Return how many entries are included in this snapshot."""
        return len(self.entries)

    @property
    def recent_risk_levels(self) -> list[str]:
        """Return recent risk levels in snapshot order."""
        return [entry.risk_level for entry in self.entries]

    @property
    def readable_summary(self) -> str:
        """Return a concise human-readable summary for manual verification."""
        if self.alert_count == 0:
            return f"No health alerts for {self.user_id}."

        noun = "alert" if self.alert_count == 1 else "alerts"
        return f"{self.alert_count} health {noun}: {', '.join(self.recent_risk_levels)}"
