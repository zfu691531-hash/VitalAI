"""Workflow entrypoint for read-only health alert history."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import HealthAlertHistoryQuery
from VitalAI.application.use_cases import (
    HealthAlertHistoryQueryResult,
    RunHealthAlertHistoryQueryUseCase,
)


@dataclass(slots=True)
class HealthAlertHistoryQueryWorkflowResult:
    """Workflow result for one health alert history query."""

    query_result: HealthAlertHistoryQueryResult


@dataclass
class HealthAlertHistoryQueryWorkflow:
    """Workflow that reads health alert history without mutating state."""

    use_case: RunHealthAlertHistoryQueryUseCase

    def run(self, query: HealthAlertHistoryQuery) -> HealthAlertHistoryQueryWorkflowResult:
        """Execute the read-only health alert history query workflow."""
        return HealthAlertHistoryQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
