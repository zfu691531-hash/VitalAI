"""Workflow entrypoint for one health alert detail query."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import HealthAlertDetailQuery
from VitalAI.application.use_cases import (
    HealthAlertDetailQueryResult,
    RunHealthAlertDetailQueryUseCase,
)


@dataclass(slots=True)
class HealthAlertDetailQueryWorkflowResult:
    """Workflow result for one health alert detail query."""

    query_result: HealthAlertDetailQueryResult


@dataclass
class HealthAlertDetailQueryWorkflow:
    """Workflow that reads one health alert entry without mutating state."""

    use_case: RunHealthAlertDetailQueryUseCase

    def run(self, query: HealthAlertDetailQuery) -> HealthAlertDetailQueryWorkflowResult:
        """Execute the read-only health alert detail query workflow."""
        return HealthAlertDetailQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
