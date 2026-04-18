"""Application use case for the minimal health alert status flow."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.commands import HealthAlertStatusUpdateCommand
from VitalAI.domains.health import HealthAlertEntry, HealthAlertRepository, HealthAlertSnapshot


@dataclass(slots=True)
class HealthAlertStatusUpdateResult:
    """Application result for one health alert status transition."""

    accepted: bool
    updated_entry: HealthAlertEntry
    previous_status: str
    snapshot: HealthAlertSnapshot


@dataclass
class RunHealthAlertStatusUpdateUseCase:
    """Mutating use case for the minimal health alert state flow."""

    repository: HealthAlertRepository

    def run(self, command: HealthAlertStatusUpdateCommand) -> HealthAlertStatusUpdateResult:
        """Update one persisted alert status and return the refreshed snapshot."""
        updated_entry, previous_status = self.repository.transition_alert_status(
            user_id=command.user_id,
            alert_id=command.alert_id,
            target_status=command.target_status,
            source_agent=command.source_agent,
            trace_id=command.trace_id,
        )
        return HealthAlertStatusUpdateResult(
            accepted=True,
            updated_entry=updated_entry,
            previous_status=previous_status,
            snapshot=self.repository.get_snapshot(user_id=command.user_id),
        )
