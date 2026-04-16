"""Workflow entrypoint for read-only mental-care check-in history."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import MentalCareCheckInHistoryQuery
from VitalAI.application.use_cases import (
    MentalCareCheckInHistoryQueryResult,
    RunMentalCareCheckInHistoryQueryUseCase,
)


@dataclass(slots=True)
class MentalCareCheckInHistoryQueryWorkflowResult:
    """Workflow result for one mental-care history query."""

    query_result: MentalCareCheckInHistoryQueryResult


@dataclass
class MentalCareCheckInHistoryQueryWorkflow:
    """Workflow that reads mental-care history without mutating state."""

    use_case: RunMentalCareCheckInHistoryQueryUseCase

    def run(self, query: MentalCareCheckInHistoryQuery) -> MentalCareCheckInHistoryQueryWorkflowResult:
        """Execute the read-only mental-care history query workflow."""
        return MentalCareCheckInHistoryQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
