"""Application use case for mental-care check-in history queries."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import MentalCareCheckInHistoryQuery
from VitalAI.domains.mental_care import MentalCareCheckInSnapshot, MentalCareCheckInSupportService


@dataclass(slots=True)
class MentalCareCheckInHistoryQueryResult:
    """Application result for one mental-care history query."""

    accepted: bool
    snapshot: MentalCareCheckInSnapshot


@dataclass
class RunMentalCareCheckInHistoryQueryUseCase:
    """Read-only use case for loading recent mental-care check-ins."""

    support_service: MentalCareCheckInSupportService

    def run(self, query: MentalCareCheckInHistoryQuery) -> MentalCareCheckInHistoryQueryResult:
        """Load recent mental-care check-in history for one user."""
        return MentalCareCheckInHistoryQueryResult(
            accepted=True,
            snapshot=self.support_service.recall_history(
                user_id=query.user_id,
                mood_filter=query.mood_filter,
                limit=query.limit,
            ),
        )
