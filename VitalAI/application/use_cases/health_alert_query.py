"""Application use case for health alert history queries."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import HealthAlertHistoryQuery
from VitalAI.domains.health import HealthAlertSnapshot, HealthAlertTriageService


@dataclass(slots=True)
class HealthAlertHistoryQueryResult:
    """Application result for one health alert history query."""

    accepted: bool
    snapshot: HealthAlertSnapshot


@dataclass
class RunHealthAlertHistoryQueryUseCase:
    """Read-only use case for loading recent health alerts."""

    triage_service: HealthAlertTriageService

    def run(self, query: HealthAlertHistoryQuery) -> HealthAlertHistoryQueryResult:
        """Load recent health alert history for one user."""
        return HealthAlertHistoryQueryResult(
            accepted=True,
            snapshot=self.triage_service.recall_history(
                user_id=query.user_id,
                status_filter=query.status_filter,
                limit=query.limit,
            ),
        )
