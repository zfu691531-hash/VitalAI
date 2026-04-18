"""Application use case for reading one daily-life check-in entry."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import DailyLifeCheckInDetailQuery
from VitalAI.domains.daily_life import DailyLifeCheckInEntry, DailyLifeCheckInSupportService


@dataclass(slots=True)
class DailyLifeCheckInDetailQueryResult:
    """Application result for one daily-life detail query."""

    accepted: bool
    entry: DailyLifeCheckInEntry


@dataclass
class RunDailyLifeCheckInDetailQueryUseCase:
    """Read-only use case for loading one persisted daily-life check-in."""

    support_service: DailyLifeCheckInSupportService

    def run(self, query: DailyLifeCheckInDetailQuery) -> DailyLifeCheckInDetailQueryResult:
        """Load one daily-life check-in entry by user and check-in id."""
        return DailyLifeCheckInDetailQueryResult(
            accepted=True,
            entry=self.support_service.recall_checkin(
                user_id=query.user_id,
                checkin_id=query.checkin_id,
            ),
        )
