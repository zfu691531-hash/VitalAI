"""typed 日常生活支持链路的 workflow 入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from VitalAI.application.commands import DailyLifeCheckInCommand
from VitalAI.application.use_cases import (
    DailyLifeCheckInFlowResult,
    RunDailyLifeCheckInFlowUseCase,
    RuntimeSignalView,
)
from VitalAI.application.workflows.reporting_support import build_feedback_report
from VitalAI.domains.reporting import FeedbackReport, FeedbackReportService
from VitalAI.platform.messaging import MessageEnvelope


@dataclass(slots=True)
class DailyLifeCheckInWorkflowResult:
    """日常生活支持链路在 workflow 层的输出。"""

    flow_result: DailyLifeCheckInFlowResult
    feedback_report: FeedbackReport | None

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime signals directly at the workflow-result boundary."""
        return self.flow_result.runtime_signals


@dataclass
class DailyLifeCheckInWorkflow:
    """从 command 出发并产出 report 的小型 workflow。"""

    use_case: RunDailyLifeCheckInFlowUseCase
    report_service: FeedbackReportService
    message_transformer: Callable[[MessageEnvelope], MessageEnvelope] = lambda envelope: envelope

    def run(self, command: DailyLifeCheckInCommand) -> DailyLifeCheckInWorkflowResult:
        """执行 typed 日常生活签到 workflow。"""
        # Keep the same boundary as the health flow: command first, then optional
        # assembly-level ingress adjustments, then runtime processing.
        message = self.message_transformer(command.to_message_envelope())
        flow_result = self.use_case.run(message)
        report = build_feedback_report(self.report_service, flow_result.outcome)
        return DailyLifeCheckInWorkflowResult(flow_result=flow_result, feedback_report=report)
