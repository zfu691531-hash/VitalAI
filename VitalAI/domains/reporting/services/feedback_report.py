"""Reporting services that consume typed feedback events."""

from __future__ import annotations

from dataclasses import dataclass, field

from VitalAI.platform.feedback import FeedbackEvent
from VitalAI.platform.security import SensitiveDataGuard


@dataclass(slots=True)
class FeedbackReportRequest:
    """Explicit reporting input derived from a feedback event."""

    trace_id: str
    agent_id: str
    task_id: str
    event_type: str
    summary: str

    @classmethod
    def from_feedback_event(cls, event: FeedbackEvent) -> "FeedbackReportRequest":
        """Create a reporting request from a typed feedback event."""
        return cls(
            trace_id=event.trace_id,
            agent_id=event.agent_id,
            task_id=event.task_id,
            event_type=event.event_type,
            summary=event.summary,
        )


@dataclass(slots=True)
class FeedbackReport:
    """Minimal reporting output built from a feedback event."""

    trace_id: str
    title: str
    body: str


@dataclass
class FeedbackReportService:
    """Minimal reporting service for typed feedback events."""

    security_guard: SensitiveDataGuard = field(default_factory=SensitiveDataGuard)

    def build_report(self, request: FeedbackReportRequest) -> FeedbackReport | None:
        """Create a small reporting-friendly summary from an explicit report request."""
        title = f"Feedback report for {request.agent_id}"
        body = (
            f"task={request.task_id}; "
            f"event={request.event_type}; "
            f"summary={request.summary}"
        )
        # reporting 是比较自然的第一道安全出口，所以这里先做轻量脱敏，
        # 后面即使接口层直接返回 report，也不会把明显的敏感文本原样带出去。
        body, _ = self.security_guard.sanitize_text(body)
        return FeedbackReport(trace_id=request.trace_id, title=title, body=body)


@dataclass
class NoOpFeedbackReportService(FeedbackReportService):
    """Reporting service variant used when reporting is intentionally disabled."""

    def build_report(self, request: FeedbackReportRequest) -> FeedbackReport | None:
        """Skip report generation while preserving the workflow contract."""
        return None
