"""Profile-memory domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProfileMemoryEntry:
    """One persisted long-term profile-memory entry."""

    user_id: str
    memory_key: str
    memory_value: str
    source_agent: str
    trace_id: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ProfileMemorySnapshot:
    """A read-model snapshot of one user's known long-term memories."""

    user_id: str
    entries: list[ProfileMemoryEntry] = field(default_factory=list)

    @property
    def memory_count(self) -> int:
        """Return how many entries are currently known for the user."""
        return len(self.entries)
