"""Workflow entrypoint for one mental-care check-in detail query."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import MentalCareCheckInDetailQuery
from VitalAI.application.use_cases import (
    MentalCareCheckInDetailQueryResult,
    RunMentalCareCheckInDetailQueryUseCase,
)


@dataclass(slots=True)
class MentalCareCheckInDetailQueryWorkflowResult:
    """Workflow result for one mental-care detail query."""

    query_result: MentalCareCheckInDetailQueryResult


@dataclass
class MentalCareCheckInDetailQueryWorkflow:
    """Workflow that reads one mental-care check-in without mutating state."""

    use_case: RunMentalCareCheckInDetailQueryUseCase

    def run(self, query: MentalCareCheckInDetailQuery) -> MentalCareCheckInDetailQueryWorkflowResult:
        """Execute the read-only mental-care detail query workflow."""
        return MentalCareCheckInDetailQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
