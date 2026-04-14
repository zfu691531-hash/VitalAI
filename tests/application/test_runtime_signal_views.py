"""Tests for application-level runtime signal view contracts."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest

from VitalAI.application import RuntimeSignalView, build_runtime_signal_views
from VitalAI.application.use_cases.health_alert_flow import HealthAlertFlowResult
from VitalAI.platform.observability import (
    ObservationKind,
    ObservationRecord,
    ObservationSeverity,
)


class RuntimeSignalViewTests(unittest.TestCase):
    def test_build_runtime_signal_views_curates_event_summary_details(self) -> None:
        records = [
            ObservationRecord(
                source="health-agent",
                kind=ObservationKind.EVENT_SUMMARY,
                severity=ObservationSeverity.WARNING,
                summary="Observed event summary HEALTH_ALERT",
                trace_id="trace-runtime-signal-1",
                observed_at=datetime.now(UTC),
                attributes={
                    "event_type": "HEALTH_ALERT",
                    "priority": "CRITICAL",
                    "target_agent": "decision-core",
                    "message_id": "hidden-message-id",
                },
            )
        ]

        views = build_runtime_signal_views(records)

        self.assertEqual(1, len(views))
        self.assertIsInstance(views[0], RuntimeSignalView)
        self.assertEqual("EVENT_SUMMARY", views[0].kind)
        self.assertEqual(
            {
                "event_type": "HEALTH_ALERT",
                "priority": "CRITICAL",
                "target_agent": "decision-core",
            },
            views[0].details,
        )

    def test_flow_result_can_expose_runtime_signals_directly(self) -> None:
        result = HealthAlertFlowResult(
            accepted=True,
            summary=None,
            outcome=None,
            runtime_observations=[
                ObservationRecord(
                    source="health-agent",
                    kind=ObservationKind.EVENT_SUMMARY,
                    severity=ObservationSeverity.WARNING,
                    summary="Observed event summary HEALTH_ALERT",
                    trace_id="trace-runtime-signal-3",
                    observed_at=datetime.now(UTC),
                    attributes={
                        "event_type": "HEALTH_ALERT",
                        "priority": "CRITICAL",
                        "target_agent": "decision-core",
                    },
                )
            ],
        )

        self.assertEqual(1, len(result.runtime_signals))
        self.assertEqual("EVENT_SUMMARY", result.runtime_signals[0].kind)

    def test_build_runtime_signal_views_curates_security_review_details(self) -> None:
        records = [
            ObservationRecord(
                source="runtime-security",
                kind=ObservationKind.SECURITY_REVIEW,
                severity=ObservationSeverity.WARNING,
                summary="Observed security review for EVENT_SUMMARY",
                trace_id="trace-runtime-signal-2",
                observed_at=datetime.now(UTC),
                attributes={
                    "signal_type": "EVENT_SUMMARY",
                    "action": "REDACT",
                    "finding_count": 1,
                    "highest_severity": "WARNING",
                    "sanitized_fields": ["contact_phone"],
                },
            )
        ]

        views = build_runtime_signal_views(records)

        self.assertEqual(1, len(views))
        self.assertEqual("SECURITY_REVIEW", views[0].kind)
        self.assertEqual(
            {
                "signal_type": "EVENT_SUMMARY",
                "action": "REDACT",
                "finding_count": 1,
                "highest_severity": "WARNING",
            },
            views[0].details,
        )


if __name__ == "__main__":
    unittest.main()
