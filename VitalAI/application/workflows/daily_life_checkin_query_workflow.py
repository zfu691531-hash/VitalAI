"""Workflow entrypoint for read-only daily-life check-in history."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import DailyLifeCheckInHistoryQuery
from VitalAI.application.use_cases import (
    DailyLifeCheckInHistoryQueryResult,
    RunDailyLifeCheckInHistoryQueryUseCase,
)


@dataclass(slots=True)
class DailyLifeCheckInHistoryQueryWorkflowResult:
    """Workflow result for one daily-life history query."""

    query_result: DailyLifeCheckInHistoryQueryResult


@dataclass
class DailyLifeCheckInHistoryQueryWorkflow:
    """Workflow that reads daily-life history without mutating state."""

    use_case: RunDailyLifeCheckInHistoryQueryUseCase

    def run(self, query: DailyLifeCheckInHistoryQuery) -> DailyLifeCheckInHistoryQueryWorkflowResult:
        """Execute the read-only daily-life history query workflow."""
        return DailyLifeCheckInHistoryQueryWorkflowResult(
            query_result=self.use_case.run(query),
        )
