"""Decision Core runtime shell.

只负责接收结构化事件摘要并输出决策，不负责原始事件聚合、日志写入或心跳监控。
"""

from dataclasses import dataclass, field
from typing import Any, Callable


DecisionHandler = Callable[[dict[str, Any]], dict[str, Any] | None]


@dataclass
class DecisionCore:
    """最小决策核心外壳。"""

    handlers: dict[str, DecisionHandler] = field(default_factory=dict)

    def register_handler(self, event_type: str, handler: DecisionHandler) -> None:
        """注册指定事件类型的决策处理器。"""
        self.handlers[event_type] = handler

    def process_summary(self, summary: dict[str, Any]) -> dict[str, Any] | None:
        """处理结构化事件摘要并返回决策结果。"""
        event_type = str(summary.get("type", ""))
        handler = self.handlers.get(event_type)
        if handler is None:
            return None
        return handler(summary)

