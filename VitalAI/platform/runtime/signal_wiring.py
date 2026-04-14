"""Minimal runtime bridge for observability and security signal wiring."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.interrupt import InterruptSignal
from VitalAI.platform.observability.records import ObservationRecord
from VitalAI.platform.observability.service import ObservabilityCollector
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot
from VitalAI.platform.security.review import SecurityReviewResult
from VitalAI.platform.security.service import SensitiveDataGuard


@dataclass(slots=True)
class RuntimeSignalDispatch:
    """Result of dispatching one runtime signal into platform services."""

    observation: ObservationRecord
    security_review: SecurityReviewResult | None = None
    security_observation: ObservationRecord | None = None


@dataclass
class RuntimeSignalBridge:
    """Fan runtime signals into observability and security with typed results."""

    observability: ObservabilityCollector
    security_guard: SensitiveDataGuard

    def observe_event_summary(self, summary: EventSummary) -> RuntimeSignalDispatch:
        """Dispatch an event summary into observability and security."""
        observation = self.observability.record_event_summary(summary)
        security_review = self.security_guard.review_event_summary(summary)
        security_observation = self.observability.record_security_review(
            security_review,
            signal_type="EVENT_SUMMARY",
            trace_id=summary.trace_id,
        )
        return RuntimeSignalDispatch(
            observation=observation,
            security_review=security_review,
            security_observation=security_observation,
        )

    def observe_interrupt(self, signal: InterruptSignal) -> RuntimeSignalDispatch:
        """Dispatch an interrupt signal into observability and security."""
        observation = self.observability.record_interrupt(signal)
        security_review = self.security_guard.review_interrupt_signal(signal)
        security_observation = self.observability.record_security_review(
            security_review,
            signal_type="INTERRUPT_SIGNAL",
            trace_id=signal.trace_id,
        )
        return RuntimeSignalDispatch(
            observation=observation,
            security_review=security_review,
            security_observation=security_observation,
        )

    def observe_snapshot(self, snapshot: RuntimeSnapshot) -> RuntimeSignalDispatch:
        """Dispatch a runtime snapshot into observability and security."""
        observation = self.observability.record_runtime_snapshot(snapshot)
        security_review = self.security_guard.review_runtime_snapshot(snapshot)
        security_observation = self.observability.record_security_review(
            security_review,
            signal_type="RUNTIME_SNAPSHOT",
            trace_id=snapshot.snapshot_id,
        )
        return RuntimeSignalDispatch(
            observation=observation,
            security_review=security_review,
            security_observation=security_observation,
        )

    def observe_failover_transition(
        self,
        *,
        previous_node: str,
        current_node: str,
        signal: InterruptSignal | None = None,
    ) -> ObservationRecord:
        """Dispatch a failover transition into observability."""
        return self.observability.record_failover_transition(
            previous_node=previous_node,
            current_node=current_node,
            trace_id=None if signal is None else signal.trace_id,
            signal_id=None if signal is None else signal.signal_id,
            has_snapshot_refs=False if signal is None else signal.has_snapshot_refs(),
            snapshot_ids=[]
            if signal is None
            else [reference.snapshot_id for reference in signal.snapshot_refs],
        )
