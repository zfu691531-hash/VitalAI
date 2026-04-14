"""typed 精神关怀支持流使用的命令对象。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.messaging import MessageEnvelope, MessagePriority


@dataclass(slots=True)
class MentalCareCheckInCommand:
    """精神关怀签到场景的稳定应用命令。"""

    source_agent: str
    trace_id: str
    user_id: str
    mood_signal: str
    support_need: str = "companionship"
    target_agent: str = "decision-core"

    def to_message_envelope(self) -> MessageEnvelope:
        """把命令转换成 runtime 入口消息格式。"""
        # command 只表达场景内的情绪与支持需求，
        # 运行角色带来的 ack/ttl 差异仍交给 assembly 在 ingress policy 阶段处理。
        priority = (
            MessagePriority.CRITICAL if self.mood_signal in {"distressed", "crisis"} else MessagePriority.HIGH
        )
        return MessageEnvelope(
            from_agent=self.source_agent,
            to_agent=self.target_agent,
            trace_id=self.trace_id,
            payload={
                "user_id": self.user_id,
                "mood_signal": self.mood_signal,
                "support_need": self.support_need,
            },
            msg_type="MENTAL_CARE_CHECKIN",
            priority=priority,
            ttl=30,
            require_ack=True,
        )
