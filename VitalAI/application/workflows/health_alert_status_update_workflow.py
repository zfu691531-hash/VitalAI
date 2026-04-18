"""Workflow entrypoint for minimal health alert status transitions."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application.commands import HealthAlertStatusUpdateCommand
from VitalAI.application.use_cases import (
    HealthAlertStatusUpdateResult,
    RunHealthAlertStatusUpdateUseCase,
)


@dataclass(slots=True)
class HealthAlertStatusUpdateWorkflowResult:
    """Workflow result for one health alert status transition."""

    update_result: HealthAlertStatusUpdateResult


@dataclass
class HealthAlertStatusUpdateWorkflow:
    """Workflow that mutates the minimal health alert state flow."""

    use_case: RunHealthAlertStatusUpdateUseCase

    def run(self, command: HealthAlertStatusUpdateCommand) -> HealthAlertStatusUpdateWorkflowResult:
        """Execute one status transition through the application layer."""
        return HealthAlertStatusUpdateWorkflowResult(update_result=self.use_case.run(command))
