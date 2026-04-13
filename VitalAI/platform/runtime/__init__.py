"""运行时层。

负责 Decision Core、事件聚合、健康监控、影子接管、快照和降级运行。
"""

from VitalAI.platform.runtime.decision_core import DecisionCore
from VitalAI.platform.runtime.degradation import AutonomyRule, DegradationLevel, DegradationPolicy
from VitalAI.platform.runtime.event_aggregator import EventAggregator
from VitalAI.platform.runtime.failover import FailoverCoordinator
from VitalAI.platform.runtime.health_monitor import HealthMonitor
from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot, SnapshotStore

__all__ = [
    "AutonomyRule",
    "DegradationLevel",
    "DegradationPolicy",
    "DecisionCore",
    "EventAggregator",
    "FailoverCoordinator",
    "HealthMonitor",
    "RuntimeSnapshot",
    "ShadowDecisionCore",
    "SnapshotStore",
]
