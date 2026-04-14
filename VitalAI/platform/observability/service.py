"""Lightweight observability collector for typed platform signals."""

from __future__ import annotations

from dataclasses import dataclass, field

from VitalAI.platform.interrupt import InterruptPriority, InterruptSignal
from VitalAI.platform.observability.records import (
    ObservationKind,
    ObservationRecord,
    ObservationSeverity,
)
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot
from VitalAI.platform.security.review import SecurityReviewResult, SecuritySeverity


@dataclass
class ObservabilityCollector:
    """Translate runtime and platform signals into observation records."""

    records: list[ObservationRecord] = field(default_factory=list)

    def record_event_summary(self, summary: EventSummary) -> ObservationRecord:
        """Record an event summary emitted by runtime."""
        record = ObservationRecord(
            source=summary.source_agent,
            kind=ObservationKind.EVENT_SUMMARY,
            severity=self._severity_for_event_summary(summary.event_type),
            summary=f"Observed event summary {summary.event_type}",
            trace_id=summary.trace_id,
            attributes={
                "message_id": summary.message_id,
                "event_type": summary.event_type,
                "target_agent": summary.target_agent,
                "priority": summary.priority.value,
            },
        )
        self.records.append(record)
        return record

    def record_interrupt(self, signal: InterruptSignal) -> ObservationRecord:
        """Record a runtime interrupt signal."""
        record = ObservationRecord(
            source=signal.source,
            kind=ObservationKind.INTERRUPT_SIGNAL,
            severity=self._severity_for_interrupt(signal.priority),
            summary=f"Observed interrupt {signal.action.value}",
            trace_id=signal.trace_id,
            attributes={
                "priority": signal.priority.value,
                "action": signal.action.value,
                "target": signal.target,
                "has_snapshot_refs": signal.has_snapshot_refs(),
            },
        )
        self.records.append(record)
        return record

    def record_policy_snapshot(
        self,
        *,
        runtime_role: str,
        reporting_enabled: bool,
        reporting_policy_source: str,
        runtime_signals_enabled: bool,
        runtime_signals_policy_source: str,
        require_ack_override: bool | None,
        ttl_override: int | None,
        ingress_policy_source: str,
        trace_id: str | None = None,
        source: str = "application-assembly",
    ) -> ObservationRecord:
        """Record an assembly policy snapshot."""
        record = ObservationRecord(
            source=source,
            kind=ObservationKind.POLICY_SNAPSHOT,
            severity=ObservationSeverity.INFO,
            summary=f"Observed policy snapshot for role {runtime_role}",
            trace_id=trace_id,
            attributes={
                "runtime_role": runtime_role,
                "reporting_enabled": reporting_enabled,
                "reporting_policy_source": reporting_policy_source,
                "runtime_signals_enabled": runtime_signals_enabled,
                "runtime_signals_policy_source": runtime_signals_policy_source,
                "require_ack_override": require_ack_override,
                "ttl_override": ttl_override,
                "ingress_policy_source": ingress_policy_source,
            },
        )
        self.records.append(record)
        return record

    def record_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> ObservationRecord:
        """Record a runtime snapshot capture."""
        record = ObservationRecord(
            source=snapshot.source,
            kind=ObservationKind.RUNTIME_SNAPSHOT,
            severity=ObservationSeverity.INFO,
            summary=f"Observed runtime snapshot {snapshot.snapshot_id}",
            trace_id=snapshot.trace_id,
            attributes={
                "snapshot_id": snapshot.snapshot_id,
                "version": snapshot.version,
                "payload_keys": sorted(snapshot.payload.keys()),
            },
        )
        self.records.append(record)
        return record

    def record_failover_transition(
        self,
        *,
        previous_node: str,
        current_node: str,
        trace_id: str | None = None,
        signal_id: str | None = None,
        has_snapshot_refs: bool = False,
        snapshot_ids: list[str] | None = None,
        source: str = "failover-coordinator",
    ) -> ObservationRecord:
        """Record a runtime failover or failback transition."""
        record = ObservationRecord(
            source=source,
            kind=ObservationKind.FAILOVER_TRANSITION,
            severity=ObservationSeverity.CRITICAL
            if current_node == "shadow"
            else ObservationSeverity.INFO,
            summary=f"Observed failover transition {previous_node}->{current_node}",
            trace_id=trace_id,
            attributes={
                "previous_node": previous_node,
                "current_node": current_node,
                "signal_id": signal_id,
                "has_snapshot_refs": has_snapshot_refs,
                "snapshot_ids": [] if snapshot_ids is None else list(snapshot_ids),
            },
        )
        self.records.append(record)
        return record

    def record_security_review(
        self,
        review: SecurityReviewResult,
        *,
        signal_type: str,
        trace_id: str | None = None,
        source: str = "runtime-security",
    ) -> ObservationRecord:
        """Record the result of a security review over a runtime signal."""
        record = ObservationRecord(
            source=source,
            kind=ObservationKind.SECURITY_REVIEW,
            severity=self._severity_for_security_review(review),
            summary=f"Observed security review for {signal_type}",
            trace_id=trace_id,
            attributes={
                "signal_type": signal_type,
                "action": review.action.value,
                "finding_count": len(review.findings),
                "highest_severity": review.highest_severity().value,
                "sanitized_fields": list(review.sanitized_fields),
                "categories": [finding.category for finding in review.findings],
            },
        )
        self.records.append(record)
        return record

    def latest(self) -> ObservationRecord | None:
        """Return the most recent observation record."""
        if not self.records:
            return None
        return self.records[-1]

    @staticmethod
    def _severity_for_event_summary(event_type: str) -> ObservationSeverity:
        """Map event types to a lightweight severity."""
        if "ALERT" in event_type or "INTERRUPT" in event_type:
            return ObservationSeverity.WARNING
        return ObservationSeverity.INFO

    @staticmethod
    def _severity_for_interrupt(priority: InterruptPriority) -> ObservationSeverity:
        """Map interrupt priority to observation severity."""
        if priority in {InterruptPriority.P0, InterruptPriority.P1}:
            return ObservationSeverity.CRITICAL
        return ObservationSeverity.WARNING

    @staticmethod
    def _severity_for_security_review(review: SecurityReviewResult) -> ObservationSeverity:
        """Map security review output to observation severity."""
        if any(finding.severity is SecuritySeverity.CRITICAL for finding in review.findings):
            return ObservationSeverity.CRITICAL
        if review.findings:
            return ObservationSeverity.WARNING
        return ObservationSeverity.INFO
