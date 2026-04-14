"""可观测性层。
负责日志、指标、链路追踪和审计记录，支持排查与运维。
"""

from VitalAI.platform.observability.records import (
    ObservationKind,
    ObservationRecord,
    ObservationSeverity,
)
from VitalAI.platform.observability.service import ObservabilityCollector

__all__ = [
    "ObservationKind",
    "ObservationRecord",
    "ObservationSeverity",
    "ObservabilityCollector",
]
