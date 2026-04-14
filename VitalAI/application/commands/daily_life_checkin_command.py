"""typed 日常生活支持流使用的命令对象。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.messaging import MessageEnvelope, MessagePriority


@dataclass(slots=True)
class DailyLifeCheckInCommand:
    """日常生活支持签到场景的稳定应用命令。"""

    source_agent: str
    trace_id: str
    user_id: str
    need: str
    urgency: str = "normal"
    target_agent: str = "decision-core"

    def to_message_envelope(self) -> MessageEnvelope:
        """把命令转换成 runtime 入口消息格式。"""
        # command 只表达 daily_life 场景自身的紧急程度，
        # 不直接承担 scheduler / consumer 这类运行语义。
        priority = MessagePriority.CRITICAL if self.urgency == "high" else MessagePriority.HIGH
        return MessageEnvelope(
            from_agent=self.source_agent,
            to_agent=self.target_agent,
            trace_id=self.trace_id,
            payload={"user_id": self.user_id, "need": self.need, "urgency": self.urgency},
            msg_type="DAILY_LIFE_CHECKIN",
            priority=priority,
            ttl=30,
            require_ack=True,
        )
