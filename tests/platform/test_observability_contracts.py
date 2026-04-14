"""Minimal tests for platform observability contracts."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest

from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal
from VitalAI.platform.messaging import MessagePriority
from VitalAI.platform.observability import (
    ObservationKind,
    ObservationSeverity,
    ObservabilityCollector,
)
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot
from VitalAI.platform.security import SecurityAction, SecurityReviewResult


class ObservabilityContractTests(unittest.TestCase):
    def test_collector_records_event_summary(self) -> None:
        collector = ObservabilityCollector()
        summary = EventSummary(
            message_id="m-obs-1",
            trace_id="t-obs-1",
            event_type="HEALTH_ALERT",
            source_agent="health-agent",
            target_agent="decision-core",
            priority=MessagePriority.CRITICAL,
            timestamp=datetime.now(UTC),
            payload={"risk_level": "critical"},
        )

        record = collector.record_event_summary(summary)

        self.assertEqual(ObservationKind.EVENT_SUMMARY, record.kind)
        self.assertEqual(ObservationSeverity.WARNING, record.severity)
        self.assertEqual("t-obs-1", record.trace_id)
        self.assertEqual("HEALTH_ALERT", record.attributes["event_type"])

    def test_collector_records_interrupt_signal(self) -> None:
        collector = ObservabilityCollector()
        signal = InterruptSignal(
            trace_id="t-obs-2",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason="primary unavailable",
            target="decision-core",
        )

        record = collector.record_interrupt(signal)

        self.assertEqual(ObservationKind.INTERRUPT_SIGNAL, record.kind)
        self.assertEqual(ObservationSeverity.CRITICAL, record.severity)
        self.assertEqual("TAKEOVER", record.attributes["action"])
        self.assertEqual("decision-core", record.attributes["target"])

    def test_collector_records_policy_snapshot(self) -> None:
        collector = ObservabilityCollector()

        record = collector.record_policy_snapshot(
            runtime_role="scheduler",
            reporting_enabled=False,
            reporting_policy_source="role_default",
            runtime_signals_enabled=True,
            runtime_signals_policy_source="environment_override",
            require_ack_override=False,
            ttl_override=300,
            ingress_policy_source="role_default",
            trace_id="policy-scheduler",
        )

        self.assertEqual(ObservationKind.POLICY_SNAPSHOT, record.kind)
        self.assertEqual(ObservationSeverity.INFO, record.severity)
        self.assertFalse(record.attributes["reporting_enabled"])
        self.assertEqual("role_default", record.attributes["reporting_policy_source"])
        self.assertTrue(record.attributes["runtime_signals_enabled"])
        self.assertEqual("environment_override", record.attributes["runtime_signals_policy_source"])
        self.assertEqual(300, record.attributes["ttl_override"])
        self.assertEqual("role_default", record.attributes["ingress_policy_source"])

    def test_collector_records_runtime_snapshot(self) -> None:
        collector = ObservabilityCollector()
        snapshot = RuntimeSnapshot(
            snapshot_id="snap-obs-1",
            created_at=datetime.now(UTC),
            source="decision-core",
            payload={"state": "warm"},
            trace_id="trace-snap-obs-1",
        )

        record = collector.record_runtime_snapshot(snapshot)

        self.assertEqual(ObservationKind.RUNTIME_SNAPSHOT, record.kind)
        self.assertEqual("snap-obs-1", record.attributes["snapshot_id"])
        self.assertEqual("trace-snap-obs-1", record.trace_id)
        self.assertEqual(["state"], record.attributes["payload_keys"])

    def test_collector_records_failover_transition(self) -> None:
        collector = ObservabilityCollector()

        record = collector.record_failover_transition(
            previous_node="primary",
            current_node="shadow",
            trace_id="trace-failover",
            signal_id="signal-1",
            has_snapshot_refs=True,
            snapshot_ids=["snap-1"],
        )

        self.assertEqual(ObservationKind.FAILOVER_TRANSITION, record.kind)
        self.assertEqual(ObservationSeverity.CRITICAL, record.severity)
        self.assertEqual("shadow", record.attributes["current_node"])
        self.assertTrue(record.attributes["has_snapshot_refs"])
        self.assertEqual(["snap-1"], record.attributes["snapshot_ids"])

    def test_collector_records_security_review(self) -> None:
        collector = ObservabilityCollector()
        review = SecurityReviewResult(
            action=SecurityAction.REDACT,
            findings=[],
            sanitized_fields=["contact_phone"],
        )

        record = collector.record_security_review(
            review,
            signal_type="EVENT_SUMMARY",
            trace_id="trace-sec-review",
        )

        self.assertEqual(ObservationKind.SECURITY_REVIEW, record.kind)
        self.assertEqual(ObservationSeverity.INFO, record.severity)
        self.assertEqual("REDACT", record.attributes["action"])
        self.assertEqual("INFO", record.attributes["highest_severity"])
        self.assertEqual(["contact_phone"], record.attributes["sanitized_fields"])


if __name__ == "__main__":
    unittest.main()
