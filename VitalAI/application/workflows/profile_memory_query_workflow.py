"""Workflow entrypoint for read-only profile-memory snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import ProfileMemorySnapshotQuery
from VitalAI.application.use_cases import ProfileMemoryQueryResult, RunProfileMemoryQueryUseCase


@dataclass(slots=True)
class ProfileMemoryQueryWorkflowResult:
    """Workflow result for one profile-memory snapshot query."""

    query_result: ProfileMemoryQueryResult


@dataclass
class ProfileMemoryQueryWorkflow:
    """Workflow that reads profile memory without mutating state."""

    use_case: RunProfileMemoryQueryUseCase

    def run(self, query: ProfileMemorySnapshotQuery) -> ProfileMemoryQueryWorkflowResult:
        """Execute the read-only profile-memory query workflow."""
        return ProfileMemoryQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
