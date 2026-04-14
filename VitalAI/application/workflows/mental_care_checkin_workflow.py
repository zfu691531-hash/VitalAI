"""typed 精神关怀支持链路的 workflow 入口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from VitalAI.application.commands import MentalCareCheckInCommand
from VitalAI.application.use_cases import (
    MentalCareCheckInFlowResult,
    RunMentalCareCheckInFlowUseCase,
    RuntimeSignalView,
)
from VitalAI.application.workflows.reporting_support import build_feedback_report
from VitalAI.domains.reporting import FeedbackReport, FeedbackReportService
from VitalAI.platform.messaging import MessageEnvelope


@dataclass(slots=True)
class MentalCareCheckInWorkflowResult:
    """精神关怀支持链路在 workflow 层的输出。"""

    flow_result: MentalCareCheckInFlowResult
    feedback_report: FeedbackReport | None

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime signals directly at the workflow-result boundary."""
        return self.flow_result.runtime_signals


@dataclass
class MentalCareCheckInWorkflow:
    """从 command 出发并产出 report 的小型 workflow。"""

    use_case: RunMentalCareCheckInFlowUseCase
    report_service: FeedbackReportService
    message_transformer: Callable[[MessageEnvelope], MessageEnvelope] = lambda envelope: envelope

    def run(self, command: MentalCareCheckInCommand) -> MentalCareCheckInWorkflowResult:
        """执行 typed 精神关怀签到 workflow。"""
        # 保持与前两条 flow 一致的边界：先产出业务消息，再由 assembly 处理运行角色差异。
        message = self.message_transformer(command.to_message_envelope())
        flow_result = self.use_case.run(message)
        report = build_feedback_report(self.report_service, flow_result.outcome)
        return MentalCareCheckInWorkflowResult(flow_result=flow_result, feedback_report=report)
