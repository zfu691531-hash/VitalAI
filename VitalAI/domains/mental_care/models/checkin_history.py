"""Mental-care check-in history read models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MentalCareCheckInEntry:
    """One persisted mental-care check-in entry."""

    user_id: str
    mood_signal: str
    support_need: str
    source_agent: str
    trace_id: str
    message_id: str
    created_at: str


@dataclass(slots=True)
class MentalCareCheckInSnapshot:
    """A read-model snapshot of recent mental-care check-ins for one user."""

    user_id: str
    entries: list[MentalCareCheckInEntry] = field(default_factory=list)

    @property
    def checkin_count(self) -> int:
        """Return how many entries are included in this snapshot."""
        return len(self.entries)

    @property
    def recent_mood_signals(self) -> list[str]:
        """Return recent mood signals in snapshot order."""
        return [entry.mood_signal for entry in self.entries]

    @property
    def recent_support_needs(self) -> list[str]:
        """Return recent support needs in snapshot order."""
        return [entry.support_need for entry in self.entries]

    @property
    def readable_summary(self) -> str:
        """Return a concise human-readable summary for manual verification."""
        if self.checkin_count == 0:
            return f"No mental-care check-ins for {self.user_id}."

        noun = "check-in" if self.checkin_count == 1 else "check-ins"
        return f"{self.checkin_count} mental-care {noun}: {', '.join(self.recent_mood_signals)}"
