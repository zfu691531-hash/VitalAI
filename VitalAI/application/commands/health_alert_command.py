"""typed 健康预警流使用的命令对象。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.messaging import MessageEnvelope, MessagePriority


@dataclass(slots=True)
class HealthAlertCommand:
    """健康预警场景的稳定应用命令。"""

    source_agent: str
    trace_id: str
    user_id: str
    risk_level: str
    target_agent: str = "decision-core"

    def to_message_envelope(self) -> MessageEnvelope:
        """把命令转换成 runtime 入口消息格式。"""
        # 这里先给出场景本身的业务优先级；如果运行角色需要额外策略，
        # assembly 会在 ingress policy 阶段继续做轻量覆盖。
        priority = MessagePriority.CRITICAL if self.risk_level == "critical" else MessagePriority.HIGH
        return MessageEnvelope(
            from_agent=self.source_agent,
            to_agent=self.target_agent,
            trace_id=self.trace_id,
            payload={"user_id": self.user_id, "risk_level": self.risk_level},
            msg_type="HEALTH_ALERT",
            priority=priority,
            ttl=30,
            require_ack=True,
        )
