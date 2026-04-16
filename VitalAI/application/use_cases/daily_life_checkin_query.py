"""Application use case for daily-life check-in history queries."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import DailyLifeCheckInHistoryQuery
from VitalAI.domains.daily_life import DailyLifeCheckInSnapshot, DailyLifeCheckInSupportService


@dataclass(slots=True)
class DailyLifeCheckInHistoryQueryResult:
    """Application result for one daily-life history query."""

    accepted: bool
    snapshot: DailyLifeCheckInSnapshot


@dataclass
class RunDailyLifeCheckInHistoryQueryUseCase:
    """Read-only use case for loading recent daily-life check-ins."""

    support_service: DailyLifeCheckInSupportService

    def run(self, query: DailyLifeCheckInHistoryQuery) -> DailyLifeCheckInHistoryQueryResult:
        """Load recent daily-life check-in history for one user."""
        return DailyLifeCheckInHistoryQueryResult(
            accepted=True,
            snapshot=self.support_service.recall_history(
                user_id=query.user_id,
                limit=query.limit,
            ),
        )
