"""Health Monitor runtime shell.

负责监控关键组件和 Agent 心跳，后续可接入告警、重启与故障切换。
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class HealthMonitor:
    """最小健康监控器外壳。"""

    heartbeat_registry: dict[str, datetime] = field(default_factory=dict)

    def heartbeat(self, component_id: str) -> None:
        """记录组件心跳。"""
        self.heartbeat_registry[component_id] = datetime.now(UTC)

    def last_seen(self, component_id: str) -> datetime | None:
        """查询组件最近心跳时间。"""
        return self.heartbeat_registry.get(component_id)

