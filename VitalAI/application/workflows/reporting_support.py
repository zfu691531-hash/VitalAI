"""Shared helpers for workflow-level reporting consumption."""

from __future__ import annotations

from typing import Protocol

from VitalAI.domains.reporting import FeedbackReport, FeedbackReportRequest, FeedbackReportService
from VitalAI.platform.feedback import FeedbackEvent


class FeedbackOutcomeProtocol(Protocol):
    """Minimal protocol for outcomes that carry a typed feedback event."""

    feedback_event: FeedbackEvent


def build_feedback_report(
    report_service: FeedbackReportService,
    outcome: FeedbackOutcomeProtocol | None,
) -> FeedbackReport | None:
    """Build a reporting output from an outcome when feedback is available."""
    if outcome is None:
        return None
    request = FeedbackReportRequest.from_feedback_event(outcome.feedback_event)
    return report_service.build_report(request)
