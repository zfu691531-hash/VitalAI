"""Application use case for profile-memory read queries."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import ProfileMemorySnapshotQuery
from VitalAI.domains.profile_memory.services import ProfileMemoryQueryOutcome, ProfileMemoryUpdateService


@dataclass(slots=True)
class ProfileMemoryQueryResult:
    """Application result for one profile-memory snapshot query."""

    accepted: bool
    outcome: ProfileMemoryQueryOutcome


@dataclass
class RunProfileMemoryQueryUseCase:
    """Read-only use case for loading one user's profile-memory snapshot."""

    memory_service: ProfileMemoryUpdateService

    def run(self, query: ProfileMemorySnapshotQuery) -> ProfileMemoryQueryResult:
        """Load the current profile-memory snapshot for one user."""
        return ProfileMemoryQueryResult(
            accepted=True,
            outcome=self.memory_service.recall_snapshot(user_id=query.user_id),
        )
