"""Minimal tests for platform security contracts."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest

from VitalAI.domains.reporting import FeedbackReportRequest, FeedbackReportService
from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal
from VitalAI.platform.messaging import MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot
from VitalAI.platform.security import SecurityAction, SecuritySeverity, SensitiveDataGuard


class SecurityContractTests(unittest.TestCase):
    def test_guard_sanitizes_sensitive_mapping_fields(self) -> None:
        guard = SensitiveDataGuard()

        payload, review = guard.sanitize_mapping(
            {
                "user_id": "elder-001",
                "contact_phone": "13800138000",
                "email": "test@example.com",
            }
        )

        self.assertEqual("[REDACTED]", payload["contact_phone"])
        self.assertEqual("[REDACTED]", payload["email"])
        self.assertEqual(SecurityAction.REDACT, review.action)
        self.assertIn("contact_phone", review.sanitized_fields)
        self.assertIn("email", review.sanitized_fields)

    def test_guard_sanitizes_sensitive_text(self) -> None:
        guard = SensitiveDataGuard()

        text, review = guard.sanitize_text("Call 13800138000 or mail test@example.com")

        self.assertNotIn("13800138000", text)
        self.assertNotIn("test@example.com", text)
        self.assertEqual(SecurityAction.REDACT, review.action)

    def test_guard_reviews_runtime_event_summary(self) -> None:
        guard = SensitiveDataGuard()
        summary = EventSummary(
            message_id="m-sec-1",
            trace_id="t-sec-1",
            event_type="HEALTH_ALERT",
            source_agent="health-agent",
            target_agent="decision-core",
            priority=MessagePriority.CRITICAL,
            timestamp=datetime.now(UTC),
            payload={"contact_phone": "13800138000"},
        )

        review = guard.review_event_summary(summary)

        self.assertEqual(SecurityAction.REDACT, review.action)
        self.assertIn("contact_phone", review.sanitized_fields)
        self.assertEqual(SecuritySeverity.WARNING, review.highest_severity())

    def test_guard_reviews_interrupt_signal(self) -> None:
        guard = SensitiveDataGuard()
        signal = InterruptSignal(
            trace_id="t-sec-2",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason="contact test@example.com immediately",
            payload={"contact_phone": "13800138000"},
        )

        review = guard.review_interrupt_signal(signal)

        self.assertEqual(SecurityAction.REDACT, review.action)
        self.assertIn("email", review.sanitized_fields)
        self.assertIn("contact_phone", review.sanitized_fields)
        self.assertEqual(SecuritySeverity.WARNING, review.highest_severity())

    def test_guard_reviews_runtime_snapshot(self) -> None:
        guard = SensitiveDataGuard()
        snapshot = RuntimeSnapshot(
            snapshot_id="snap-sec-1",
            created_at=datetime.now(UTC),
            source="decision-core",
            payload={"emergency_phone": "13800138000"},
        )

        review = guard.review_runtime_snapshot(snapshot)

        self.assertEqual(SecurityAction.REDACT, review.action)
        self.assertIn("emergency_phone", review.sanitized_fields)
        self.assertEqual(SecuritySeverity.WARNING, review.highest_severity())

    def test_guard_reviews_nested_runtime_snapshot_payload(self) -> None:
        guard = SensitiveDataGuard()
        snapshot = RuntimeSnapshot(
            snapshot_id="snap-sec-2",
            created_at=datetime.now(UTC),
            source="decision-core",
            payload={
                "event_payload": {
                    "contact_phone": "13800138000",
                    "notes": ["mail test@example.com"],
                }
            },
        )

        review = guard.review_runtime_snapshot(snapshot)

        self.assertEqual(SecurityAction.REDACT, review.action)
        self.assertIn("event_payload.contact_phone", review.sanitized_fields)
        self.assertIn("event_payload.notes[0]", review.sanitized_fields)

    def test_guard_does_not_treat_technical_message_id_as_phone_data(self) -> None:
        guard = SensitiveDataGuard()
        signal = InterruptSignal(
            trace_id="t-sec-3",
            source="typed-flow-runtime",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason="controlled drill",
            payload={"message_id": "8f5df3953777446a8c4375fdcb280840"},
        )

        review = guard.review_interrupt_signal(signal)

        self.assertEqual(SecurityAction.ALLOW, review.action)
        self.assertEqual([], review.sanitized_fields)

    def test_review_without_findings_reports_info_highest_severity(self) -> None:
        guard = SensitiveDataGuard()

        _, review = guard.sanitize_text("normal operational summary")

        self.assertEqual(SecurityAction.ALLOW, review.action)
        self.assertEqual(SecuritySeverity.INFO, review.highest_severity())

    def test_feedback_report_service_redacts_sensitive_summary(self) -> None:
        service = FeedbackReportService()

        report = service.build_report(
            FeedbackReportRequest(
                trace_id="trace-sec-1",
                agent_id="health-domain-service",
                task_id="task-1",
                event_type="COMPLETED",
                summary="Follow up with test@example.com and 13800138000",
            )
        )

        self.assertIsNotNone(report)
        self.assertNotIn("test@example.com", report.body)
        self.assertNotIn("13800138000", report.body)
        self.assertIn("[REDACTED]", report.body)


if __name__ == "__main__":
    unittest.main()
