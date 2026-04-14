"""平台可观测层使用的 typed 观测记录。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class ObservationKind(StrEnum):
    """观测记录的事件类型。"""

    EVENT_SUMMARY = "EVENT_SUMMARY"
    INTERRUPT_SIGNAL = "INTERRUPT_SIGNAL"
    POLICY_SNAPSHOT = "POLICY_SNAPSHOT"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    RUNTIME_SNAPSHOT = "RUNTIME_SNAPSHOT"
    FAILOVER_TRANSITION = "FAILOVER_TRANSITION"


class ObservationSeverity(StrEnum):
    """观测记录的严重程度。"""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class ObservationRecord:
    """供日志、指标、审计等入口复用的最小 typed 观测记录。"""

    source: str
    kind: ObservationKind
    severity: ObservationSeverity
    summary: str
    attributes: dict[str, object] = field(default_factory=dict)
    trace_id: str | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    observation_id: str = field(default_factory=lambda: f"obs-{uuid4().hex}")
