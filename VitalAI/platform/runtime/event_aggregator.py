"""Event Aggregator runtime shell.

负责接收原始事件，后续将扩展为去重、合并、优先级排序、TTL 校验和置信度预检。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventAggregator:
    """最小事件聚合器外壳。"""

    raw_events: list[dict[str, Any]] = field(default_factory=list)

    def ingest(self, event: dict[str, Any]) -> None:
        """接收原始事件。"""
        self.raw_events.append(event)

    def summarize(self) -> list[dict[str, Any]]:
        """输出当前摘要结果。

        当前仅返回原始事件列表，后续再逐步加入聚合逻辑。
        """
        return list(self.raw_events)

