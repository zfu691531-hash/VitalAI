"""Minimal tests for runtime wiring against platform contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.observability import ObservationKind, ObservabilityCollector
from VitalAI.platform.runtime import (
    DEFAULT_RUNTIME_SNAPSHOT_POLICY,
    DecisionCore,
    DegradationLevel,
    DegradationPolicy,
    EventAggregator,
    HealthMonitor,
    SnapshotStore,
)
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.failover import FailoverCoordinator
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge
from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore
from VitalAI.platform.security import SensitiveDataGuard


class RuntimeContractWiringTests(unittest.TestCase):
    def test_event_aggregator_emits_typed_summary(self) -> None:
        aggregator = EventAggregator()
        event = MessageEnvelope(
            from_agent="health-agent",
            to_agent="decision-core",
            payload={"risk_level": "high"},
            msg_type="HEALTH_ALERT",
            priority=MessagePriority.CRITICAL,
            ttl=30,
        )

        accepted = aggregator.ingest(event)
        summaries = aggregator.summarize()

        self.assertTrue(accepted)
        self.assertEqual(1, len(summaries))
        self.assertIsInstance(summaries[0], EventSummary)
        self.assertEqual("HEALTH_ALERT", summaries[0].event_type)

    def test_default_runtime_snapshot_policy_matches_critical_health_alert(self) -> None:
        decision = DEFAULT_RUNTIME_SNAPSHOT_POLICY.decide(
            EventSummary(
                message_id="m-policy-1",
                trace_id="t-policy-1",
                event_type="HEALTH_ALERT",
                source_agent="health-agent",
                target_agent="decision-core",
                priority=MessagePriority.CRITICAL,
                timestamp=datetime.now(UTC),
                payload={"risk_level": "critical"},
            )
        )

        self.assertIsNotNone(decision)
        self.assertEqual("critical_health_alert", decision.policy_name)

    def test_default_runtime_snapshot_policy_matches_high_urgency_daily_life(self) -> None:
        decision = DEFAULT_RUNTIME_SNAPSHOT_POLICY.decide(
            EventSummary(
                message_id="m-policy-2",
                trace_id="t-policy-2",
                event_type="DAILY_LIFE_CHECKIN",
                source_agent="daily-agent",
                target_agent="decision-core",
                priority=MessagePriority.CRITICAL,
                timestamp=datetime.now(UTC),
                payload={"urgency": "high", "need": "meal_support"},
            )
        )

        self.assertIsNotNone(decision)
        self.assertEqual("high_urgency_daily_life_checkin", decision.policy_name)

    def test_default_runtime_snapshot_policy_skips_non_matching_summary(self) -> None:
        decision = DEFAULT_RUNTIME_SNAPSHOT_POLICY.decide(
            EventSummary(
                message_id="m-policy-3",
                trace_id="t-policy-3",
                event_type="MENTAL_CARE_CHECKIN",
                source_agent="mental-agent",
                target_agent="decision-core",
                priority=MessagePriority.CRITICAL,
                timestamp=datetime.now(UTC),
                payload={"mood_signal": "distressed"},
            )
        )

        self.assertIsNone(decision)

    def test_event_aggregator_can_wire_summary_to_platform_signals(self) -> None:
        aggregator = EventAggregator()
        collector = ObservabilityCollector()
        bridge = RuntimeSignalBridge(
            observability=collector,
            security_guard=SensitiveDataGuard(),
        )
        aggregator.ingest(
            MessageEnvelope(
                from_agent="health-agent",
                to_agent="decision-core",
                payload={"contact_phone": "13800138000"},
                msg_type="HEALTH_ALERT",
                priority=MessagePriority.CRITICAL,
            )
        )

        summaries = aggregator.summarize(signal_bridge=bridge)

        self.assertEqual(1, len(summaries))
        self.assertEqual(2, len(collector.records))
        self.assertEqual(ObservationKind.EVENT_SUMMARY, collector.records[0].kind)
        self.assertEqual(ObservationKind.SECURITY_REVIEW, collector.records[1].kind)
        self.assertEqual("REDACT", collector.records[1].attributes["action"])

    def test_decision_core_returns_message_envelope(self) -> None:
        core = DecisionCore()

        def handler(summary: EventSummary) -> MessageEnvelope:
            return MessageEnvelope(
                from_agent="decision-core",
                to_agent=summary.source_agent,
                payload={"decision": "dispatch_nurse"},
                msg_type="DECISION",
            )

        core.register_handler("HEALTH_ALERT", handler)
        summary = EventSummary(
            message_id="m1",
            trace_id="t1",
            event_type="HEALTH_ALERT",
            source_agent="health-agent",
            target_agent="decision-core",
            priority=MessagePriority.CRITICAL,
            timestamp=datetime.now(UTC),
            payload={"risk_level": "high"},
        )

        result = core.process_summary(summary)

        self.assertIsInstance(result, MessageEnvelope)
        self.assertEqual("decision-core", result.from_agent)
        self.assertEqual("health-agent", result.to_agent)

    def test_snapshot_reference_and_failover_signal_align(self) -> None:
        store = SnapshotStore()
        snapshot = store.save("snap-1", "decision-core", {"state": "warm"})
        signal = InterruptSignal(
            trace_id="trace-1",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason="primary unavailable",
            snapshot_refs=[snapshot.to_reference()],
        )
        coordinator = FailoverCoordinator(
            primary=DecisionCore(),
            shadow=ShadowDecisionCore(latest_snapshot=snapshot),
        )

        did_failover = coordinator.failover(signal)

        self.assertTrue(did_failover)
        self.assertEqual("shadow", coordinator.active_node)

    def test_health_monitor_builds_interrupt_for_stale_component(self) -> None:
        monitor = HealthMonitor()
        observed_at = datetime.now(UTC) - timedelta(minutes=5)
        monitor.heartbeat("decision-core", observed_at=observed_at)

        signal = monitor.build_interrupt(
            "decision-core",
            timeout=timedelta(minutes=1),
            now=datetime.now(UTC),
        )

        self.assertIsNotNone(signal)
        self.assertEqual(InterruptAction.TAKEOVER, signal.action)
        self.assertEqual("decision-core", signal.target)

    def test_health_monitor_can_wire_interrupt_to_platform_signals(self) -> None:
        monitor = HealthMonitor()
        collector = ObservabilityCollector()
        bridge = RuntimeSignalBridge(
            observability=collector,
            security_guard=SensitiveDataGuard(),
        )
        observed_at = datetime.now(UTC) - timedelta(minutes=5)
        monitor.heartbeat("decision-core", observed_at=observed_at)

        signal = monitor.build_interrupt(
            "decision-core",
            timeout=timedelta(minutes=1),
            now=datetime.now(UTC),
            signal_bridge=bridge,
        )

        self.assertIsNotNone(signal)
        self.assertEqual(2, len(collector.records))
        self.assertEqual(ObservationKind.INTERRUPT_SIGNAL, collector.records[0].kind)
        self.assertEqual(ObservationKind.SECURITY_REVIEW, collector.records[1].kind)

    def test_snapshot_store_can_wire_snapshot_to_platform_signals(self) -> None:
        collector = ObservabilityCollector()
        bridge = RuntimeSignalBridge(
            observability=collector,
            security_guard=SensitiveDataGuard(),
        )
        store = SnapshotStore()

        snapshot = store.save(
            "snap-runtime-1",
            "decision-core",
            {"contact_phone": "13800138000"},
            trace_id="trace-snap-runtime-1",
            signal_bridge=bridge,
        )

        self.assertEqual("snap-runtime-1", snapshot.snapshot_id)
        self.assertEqual("trace-snap-runtime-1", snapshot.trace_id)
        self.assertEqual(2, len(collector.records))
        self.assertEqual(ObservationKind.RUNTIME_SNAPSHOT, collector.records[0].kind)
        self.assertEqual("trace-snap-runtime-1", collector.records[0].trace_id)
        self.assertEqual(ObservationKind.SECURITY_REVIEW, collector.records[1].kind)
        self.assertEqual("REDACT", collector.records[1].attributes["action"])

    def test_failover_transition_can_emit_observation(self) -> None:
        collector = ObservabilityCollector()
        bridge = RuntimeSignalBridge(
            observability=collector,
            security_guard=SensitiveDataGuard(),
        )
        store = SnapshotStore()
        snapshot = store.save("snap-2", "decision-core", {"state": "warm"})
        signal = InterruptSignal(
            trace_id="trace-failover",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason="primary unavailable",
            snapshot_refs=[snapshot.to_reference()],
        )
        coordinator = FailoverCoordinator(
            primary=DecisionCore(),
            shadow=ShadowDecisionCore(latest_snapshot=snapshot),
        )

        did_failover = coordinator.failover(signal, signal_bridge=bridge)

        self.assertTrue(did_failover)
        self.assertEqual(1, len(collector.records))
        self.assertEqual(ObservationKind.FAILOVER_TRANSITION, collector.records[0].kind)

    def test_failback_transition_can_emit_observation_with_snapshot_correlation(self) -> None:
        collector = ObservabilityCollector()
        bridge = RuntimeSignalBridge(
            observability=collector,
            security_guard=SensitiveDataGuard(),
        )
        store = SnapshotStore()
        snapshot = store.save("snap-failback-1", "decision-core", {"state": "warm"})
        signal = InterruptSignal(
            trace_id="trace-failback",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.RESUME,
            reason="primary restored",
            snapshot_refs=[snapshot.to_reference()],
        )
        coordinator = FailoverCoordinator(
            primary=DecisionCore(),
            shadow=ShadowDecisionCore(latest_snapshot=snapshot),
            active_node="shadow",
        )

        coordinator.failback(signal=signal, signal_bridge=bridge)

        self.assertEqual("primary", coordinator.active_node)
        self.assertEqual(1, len(collector.records))
        self.assertEqual(ObservationKind.FAILOVER_TRANSITION, collector.records[0].kind)
        self.assertEqual("trace-failback", collector.records[0].trace_id)
        self.assertEqual([snapshot.snapshot_id], collector.records[0].attributes["snapshot_ids"])
        self.assertTrue(collector.records[0].attributes["has_snapshot_refs"])

    def test_degradation_policy_applies_interrupt_priority(self) -> None:
        policy = DegradationPolicy()
        signal = InterruptSignal(
            trace_id="trace-2",
            source="health-monitor",
            priority=InterruptPriority.P0,
            action=InterruptAction.ESCALATE,
            reason="system-wide failure",
        )

        level = policy.apply_interrupt(signal)

        self.assertEqual(DegradationLevel.SURVIVAL, level)
        self.assertEqual(DegradationLevel.SURVIVAL, policy.level)


if __name__ == "__main__":
    unittest.main()
