"""Workflow entrypoint for one lightweight user overview query."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import UserOverviewQuery
from VitalAI.application.use_cases.user_overview_query import (
    RunUserOverviewQueryUseCase,
    UserOverviewQueryResult,
)


@dataclass(slots=True)
class UserOverviewQueryWorkflowResult:
    """Workflow result for one user overview query."""

    query_result: UserOverviewQueryResult


@dataclass
class UserOverviewQueryWorkflow:
    """Workflow that aggregates existing user-facing snapshots without mutating state."""

    use_case: RunUserOverviewQueryUseCase

    def run(self, query: UserOverviewQuery) -> UserOverviewQueryWorkflowResult:
        """Execute the read-only user overview workflow."""
        return UserOverviewQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
