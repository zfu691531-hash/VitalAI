"""typed 健康预警编排链路的 workflow 入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from VitalAI.application.commands import HealthAlertCommand
from VitalAI.application.use_cases import (
    HealthAlertFlowResult,
    RunHealthAlertFlowUseCase,
    RuntimeSignalView,
)
from VitalAI.application.workflows.reporting_support import build_feedback_report
from VitalAI.domains.reporting import FeedbackReport, FeedbackReportService
from VitalAI.platform.messaging import MessageEnvelope


@dataclass(slots=True)
class HealthAlertWorkflowResult:
    """健康预警链路在 workflow 层的输出。"""

    flow_result: HealthAlertFlowResult
    feedback_report: FeedbackReport | None

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime signals directly at the workflow-result boundary."""
        return self.flow_result.runtime_signals


@dataclass
class HealthAlertWorkflow:
    """从 command 出发并产出 report 的小型 workflow。"""

    use_case: RunHealthAlertFlowUseCase
    report_service: FeedbackReportService
    message_transformer: Callable[[MessageEnvelope], MessageEnvelope] = lambda envelope: envelope

    def run(self, command: HealthAlertCommand) -> HealthAlertWorkflowResult:
        """执行首条 typed 健康预警 workflow。"""
        # Commands produce the domain-shaped message; assembly may still adjust
        # transport-facing fields such as ack/ttl before runtime ingestion.
        message = self.message_transformer(command.to_message_envelope())
        flow_result = self.use_case.run(message)
        report = build_feedback_report(self.report_service, flow_result.outcome)
        return HealthAlertWorkflowResult(flow_result=flow_result, feedback_report=report)
