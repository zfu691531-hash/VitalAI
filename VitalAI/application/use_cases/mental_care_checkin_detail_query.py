"""Application use case for reading one mental-care check-in entry."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import MentalCareCheckInDetailQuery
from VitalAI.domains.mental_care import MentalCareCheckInEntry, MentalCareCheckInSupportService


@dataclass(slots=True)
class MentalCareCheckInDetailQueryResult:
    """Application result for one mental-care detail query."""

    accepted: bool
    entry: MentalCareCheckInEntry


@dataclass
class RunMentalCareCheckInDetailQueryUseCase:
    """Read-only use case for loading one persisted mental-care check-in."""

    support_service: MentalCareCheckInSupportService

    def run(self, query: MentalCareCheckInDetailQuery) -> MentalCareCheckInDetailQueryResult:
        """Load one mental-care check-in entry by user and check-in id."""
        return MentalCareCheckInDetailQueryResult(
            accepted=True,
            entry=self.support_service.recall_checkin(
                user_id=query.user_id,
                checkin_id=query.checkin_id,
            ),
        )
