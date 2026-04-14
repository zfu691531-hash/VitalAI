"""Snapshot runtime primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from VitalAI.platform.interrupt import SnapshotReference
from VitalAI.platform.messaging import MessagePriority

if TYPE_CHECKING:
    from VitalAI.platform.runtime.event_aggregator import EventSummary
    from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass
class RuntimeSnapshot:
    """Runtime snapshot used for takeover and recovery."""

    snapshot_id: str
    created_at: datetime
    source: str
    payload: dict[str, Any]
    trace_id: str | None = None
    version: int = 1

    def to_reference(self) -> SnapshotReference:
        """Build an interrupt-facing reference for this snapshot."""
        return SnapshotReference(
            snapshot_id=self.snapshot_id,
            source=self.source,
            captured_at=self.created_at,
            version=self.version,
        )


@dataclass(frozen=True, slots=True)
class SnapshotCaptureDecision:
    """Typed decision describing why a runtime snapshot should be captured."""

    policy_name: str
    reason: str
    interrupt_reason: str


@dataclass(frozen=True, slots=True)
class SnapshotCaptureRule:
    """Small typed rule deciding whether one event summary should emit a snapshot."""

    event_type: str
    policy_name: str
    reason: str
    interrupt_reason: str
    priority: MessagePriority | None = None
    payload_matches: dict[str, object] = field(default_factory=dict)

    def matches(self, summary: "EventSummary") -> bool:
        """Return whether this rule applies to the current event summary."""
        if summary.event_type != self.event_type:
            return False
        if self.priority is not None and summary.priority is not self.priority:
            return False
        return all(summary.payload.get(key) == value for key, value in self.payload_matches.items())

    def decide(self) -> SnapshotCaptureDecision:
        """Build the typed capture decision for this rule."""
        return SnapshotCaptureDecision(
            policy_name=self.policy_name,
            reason=self.reason,
            interrupt_reason=self.interrupt_reason,
        )


@dataclass(frozen=True, slots=True)
class SnapshotCapturePolicy:
    """Typed runtime snapshot policy made of small explicit rules."""

    rules: tuple[SnapshotCaptureRule, ...]

    def decide(self, summary: "EventSummary") -> SnapshotCaptureDecision | None:
        """Return the first matching snapshot-capture decision for one summary."""
        for rule in self.rules:
            if rule.matches(summary):
                return rule.decide()
        return None


DEFAULT_RUNTIME_SNAPSHOT_POLICY = SnapshotCapturePolicy(
    rules=(
        SnapshotCaptureRule(
            event_type="HEALTH_ALERT",
            priority=MessagePriority.CRITICAL,
            policy_name="critical_health_alert",
            reason="critical health alert requires runtime snapshot capture",
            interrupt_reason="critical health alert captured runtime snapshot for takeover readiness",
        ),
        SnapshotCaptureRule(
            event_type="DAILY_LIFE_CHECKIN",
            priority=MessagePriority.CRITICAL,
            payload_matches={"urgency": "high"},
            policy_name="high_urgency_daily_life_checkin",
            reason="high urgency daily-life check-in requires runtime snapshot capture",
            interrupt_reason="high urgency daily-life check-in captured runtime snapshot for takeover readiness",
        ),
    )
)


@dataclass
class SnapshotStore:
    """Minimal in-memory snapshot store."""

    snapshots: dict[str, RuntimeSnapshot] = field(default_factory=dict)

    def save(
        self,
        snapshot_id: str,
        source: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> RuntimeSnapshot:
        """Save a snapshot and return the stored object."""
        snapshot = RuntimeSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(UTC),
            source=source,
            payload=payload,
            trace_id=trace_id,
        )
        self.snapshots[snapshot_id] = snapshot
        if signal_bridge is not None:
            signal_bridge.observe_snapshot(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> RuntimeSnapshot | None:
        """Return a snapshot by identifier."""
        return self.snapshots.get(snapshot_id)

    def get_reference(self, snapshot_id: str) -> SnapshotReference | None:
        """Return a snapshot reference by identifier."""
        snapshot = self.get(snapshot_id)
        if snapshot is None:
            return None
        return snapshot.to_reference()

    def latest(self) -> RuntimeSnapshot | None:
        """Return the most recently created snapshot."""
        if not self.snapshots:
            return None
        return max(self.snapshots.values(), key=lambda item: item.created_at)
