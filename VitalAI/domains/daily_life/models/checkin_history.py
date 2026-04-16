"""Daily-life check-in history read models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DailyLifeCheckInEntry:
    """One persisted daily-life check-in entry."""

    user_id: str
    need: str
    urgency: str
    source_agent: str
    trace_id: str
    message_id: str
    created_at: str


@dataclass(slots=True)
class DailyLifeCheckInSnapshot:
    """A read-model snapshot of recent daily-life check-ins for one user."""

    user_id: str
    entries: list[DailyLifeCheckInEntry] = field(default_factory=list)

    @property
    def checkin_count(self) -> int:
        """Return how many entries are included in this snapshot."""
        return len(self.entries)

    @property
    def recent_needs(self) -> list[str]:
        """Return recent need labels in snapshot order."""
        return [entry.need for entry in self.entries]

    @property
    def readable_summary(self) -> str:
        """Return a concise human-readable summary for manual verification."""
        if self.checkin_count == 0:
            return f"No daily-life check-ins for {self.user_id}."

        noun = "check-in" if self.checkin_count == 1 else "check-ins"
        return f"{self.checkin_count} daily-life {noun}: {', '.join(self.recent_needs)}"
