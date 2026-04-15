"""Runtime layer exports."""

from VitalAI.platform.runtime.decision_core import DecisionCore
from VitalAI.platform.runtime.degradation import AutonomyRule, DegradationLevel, DegradationPolicy
from VitalAI.platform.runtime.event_aggregator import EventAggregator, EventSummary
from VitalAI.platform.runtime.failover import FailoverCoordinator
from VitalAI.platform.runtime.health_monitor import HealthMonitor, HeartbeatRecord
from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore
from VitalAI.platform.runtime.snapshots import (
    DEFAULT_RUNTIME_SNAPSHOT_POLICY,
    FileSnapshotStore,
    RuntimeSnapshot,
    SnapshotCaptureDecision,
    SnapshotCapturePolicy,
    SnapshotCaptureRule,
    SnapshotStore,
)

__all__ = [
    "AutonomyRule",
    "DegradationLevel",
    "DegradationPolicy",
    "DecisionCore",
    "DEFAULT_RUNTIME_SNAPSHOT_POLICY",
    "EventAggregator",
    "EventSummary",
    "FailoverCoordinator",
    "FileSnapshotStore",
    "HealthMonitor",
    "HeartbeatRecord",
    "RuntimeSnapshot",
    "SnapshotCaptureDecision",
    "SnapshotCapturePolicy",
    "SnapshotCaptureRule",
    "ShadowDecisionCore",
    "SnapshotStore",
]
