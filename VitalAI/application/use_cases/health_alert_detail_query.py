"""Application use case for reading one health alert entry."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.queries import HealthAlertDetailQuery
from VitalAI.domains.health import HealthAlertEntry, HealthAlertTriageService


@dataclass(slots=True)
class HealthAlertDetailQueryResult:
    """Application result for one health alert detail query."""

    accepted: bool
    entry: HealthAlertEntry


@dataclass
class RunHealthAlertDetailQueryUseCase:
    """Read-only use case for loading one persisted health alert."""

    triage_service: HealthAlertTriageService

    def run(self, query: HealthAlertDetailQuery) -> HealthAlertDetailQueryResult:
        """Load one health alert entry by user and alert id."""
        return HealthAlertDetailQueryResult(
            accepted=True,
            entry=self.triage_service.recall_alert(
                user_id=query.user_id,
                alert_id=query.alert_id,
            ),
        )
