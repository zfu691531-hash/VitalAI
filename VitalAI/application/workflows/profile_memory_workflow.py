"""Workflow entrypoint for typed profile-memory updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from VitalAI.application.commands import ProfileMemoryUpdateCommand
from VitalAI.application.use_cases import (
    ProfileMemoryFlowResult,
    RunProfileMemoryFlowUseCase,
    RuntimeSignalView,
)
from VitalAI.application.workflows.reporting_support import build_feedback_report
from VitalAI.domains.reporting import FeedbackReport, FeedbackReportService
from VitalAI.platform.messaging import MessageEnvelope


@dataclass(slots=True)
class ProfileMemoryWorkflowResult:
    """Workflow result for the typed profile-memory update flow."""

    flow_result: ProfileMemoryFlowResult
    feedback_report: FeedbackReport | None

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime signals directly at the workflow-result boundary."""
        return self.flow_result.runtime_signals


@dataclass
class ProfileMemoryWorkflow:
    """Workflow that persists profile memory and builds reporting output."""

    use_case: RunProfileMemoryFlowUseCase
    report_service: FeedbackReportService
    message_transformer: Callable[[MessageEnvelope], MessageEnvelope] = lambda envelope: envelope

    def run(self, command: ProfileMemoryUpdateCommand) -> ProfileMemoryWorkflowResult:
        """Execute the typed profile-memory workflow."""
        message = self.message_transformer(command.to_message_envelope())
        flow_result = self.use_case.run(message)
        report = build_feedback_report(self.report_service, flow_result.outcome)
        return ProfileMemoryWorkflowResult(flow_result=flow_result, feedback_report=report)
