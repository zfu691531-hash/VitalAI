"""Workflow entrypoint for one daily-life check-in detail query."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import DailyLifeCheckInDetailQuery
from VitalAI.application.use_cases import (
    DailyLifeCheckInDetailQueryResult,
    RunDailyLifeCheckInDetailQueryUseCase,
)


@dataclass(slots=True)
class DailyLifeCheckInDetailQueryWorkflowResult:
    """Workflow result for one daily-life detail query."""

    query_result: DailyLifeCheckInDetailQueryResult


@dataclass
class DailyLifeCheckInDetailQueryWorkflow:
    """Workflow that reads one daily-life check-in without mutating state."""

    use_case: RunDailyLifeCheckInDetailQueryUseCase

    def run(self, query: DailyLifeCheckInDetailQuery) -> DailyLifeCheckInDetailQueryWorkflowResult:
        """Execute the read-only daily-life detail query workflow."""
        return DailyLifeCheckInDetailQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
