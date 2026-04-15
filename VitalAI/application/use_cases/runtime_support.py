"""Shared support helpers for typed runtime-backed use cases."""

from __future__ import annotations

from datetime import UTC, datetime

from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal
from VitalAI.platform.observability import ObservationRecord
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.runtime import (
    DEFAULT_RUNTIME_SNAPSHOT_POLICY,
    EventAggregator,
    EventSummary,
    RuntimeSnapshot,
    SnapshotCaptureDecision,
    SnapshotStore,
)
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


def ingest_and_get_latest_summary(
    aggregator: EventAggregator,
    event: MessageEnvelope,
    signal_bridge: RuntimeSignalBridge | None = None,
    snapshot_store: SnapshotStore | None = None,
) -> tuple[bool, EventSummary | None, list[ObservationRecord]]:
    """Ingest a message and return the latest summary and emitted observations."""
    accepted = aggregator.ingest(event)
    if not accepted:
        return False, None, []

    summaries = aggregator.summarize(signal_bridge=signal_bridge)
    if not summaries:
        return False, None, []

    latest_summary = summaries[-1]
    capture_decision = DEFAULT_RUNTIME_SNAPSHOT_POLICY.decide(latest_summary)
    if signal_bridge is not None and capture_decision is not None:
        store = snapshot_store if snapshot_store is not None else SnapshotStore()
        snapshot = store.save(
            snapshot_id=f"snapshot-{latest_summary.message_id}",
            source="typed-flow-runtime",
            payload={
                "trace_id": latest_summary.trace_id,
                "event_type": latest_summary.event_type,
                "priority": latest_summary.priority.value,
                "source_agent": latest_summary.source_agent,
                "target_agent": latest_summary.target_agent,
                "event_payload": dict(latest_summary.payload),
                "capture_policy": capture_decision.policy_name,
                "capture_reason": capture_decision.reason,
            },
            trace_id=latest_summary.trace_id,
            signal_bridge=signal_bridge,
        )
        signal_bridge.observe_interrupt(
            _build_failover_readiness_signal(
                summary=latest_summary,
                snapshot=snapshot,
                capture_decision=capture_decision,
            )
        )

    observations: list[ObservationRecord] = []
    if signal_bridge is not None:
        observations = list(signal_bridge.observability.records)
    return True, latest_summary, observations


def _build_failover_readiness_signal(
    *,
    summary: EventSummary,
    snapshot: RuntimeSnapshot,
    capture_decision: SnapshotCaptureDecision,
) -> InterruptSignal:
    """Build a minimal interrupt showing failover readiness for a critical flow."""
    return InterruptSignal(
        trace_id=summary.trace_id,
        source="typed-flow-runtime",
        priority=InterruptPriority.P1,
        action=InterruptAction.TAKEOVER,
        reason=capture_decision.interrupt_reason,
        target=summary.target_agent,
        timestamp=datetime.now(UTC),
        snapshot_refs=[snapshot.to_reference()],
        payload={
            "event_type": summary.event_type,
            "priority": summary.priority.value,
            "message_id": summary.message_id,
        },
    )
