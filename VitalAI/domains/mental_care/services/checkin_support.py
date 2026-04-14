"""第三条 typed application flow 使用的精神关怀支持服务。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.arbitration import Flexibility, GoalType, IntentDeclaration, ResourceRequirement
from VitalAI.platform.feedback import FeedbackEvent, FeedbackLayer
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary


@dataclass(slots=True)
class MentalCareSupportOutcome:
    """由精神关怀签到 summary 生成的领域层结果。"""

    decision_message: MessageEnvelope
    feedback_event: FeedbackEvent
    care_intent: IntentDeclaration


@dataclass
class MentalCareCheckInSupportService:
    """对情绪波动或陪伴需求做出响应的最小精神关怀领域服务。"""

    domain_agent_id: str = "mental-care-domain-service"

    def support(self, summary: EventSummary) -> MentalCareSupportOutcome:
        """把精神关怀签到摘要翻译成 typed 平台输出。"""
        user_id = str(summary.payload.get("user_id", "unknown-user"))
        mood_signal = str(summary.payload.get("mood_signal", "stable"))
        support_need = str(summary.payload.get("support_need", "companionship"))

        priority = (
            MessagePriority.CRITICAL if mood_signal in {"distressed", "crisis"} else MessagePriority.HIGH
        )
        # 这里继续沿用三件套输出：decision / feedback / intent。
        # 这样 mental_care 接入后，reporting 和 arbitration 不需要额外理解第三套私有格式。
        decision_message = MessageEnvelope(
            from_agent=self.domain_agent_id,
            to_agent=summary.source_agent,
            trace_id=summary.trace_id,
            payload={
                "user_id": user_id,
                "decision": "arrange_mental_care_followup",
                "mood_signal": mood_signal,
                "support_need": support_need,
            },
            msg_type="MENTAL_CARE_DECISION",
            priority=priority,
            require_ack=True,
        )

        feedback_event = FeedbackEvent(
            trace_id=summary.trace_id,
            agent_id=self.domain_agent_id,
            task_id=summary.message_id,
            event_type="COMPLETED",
            feedback_layer=FeedbackLayer.L1,
            summary=f"Mental care support triaged for {user_id} mood={mood_signal}",
            completion_rate=1.0,
            payload={
                "decision_message_id": decision_message.msg_id,
                "mood_signal": mood_signal,
                "support_need": support_need,
            },
        )

        care_intent = IntentDeclaration(
            agent_id=self.domain_agent_id,
            action="coordinate_mental_care_support",
            content_preview=f"Support {user_id} mood={mood_signal} need={support_need}",
            goal_type=GoalType.MENTAL_CARE,
            goal_weight=1.0 if mood_signal in {"distressed", "crisis"} else 0.75,
            flexibility=(
                Flexibility.FIXED if mood_signal in {"distressed", "crisis"} else Flexibility.PREFERRED
            ),
            resources_needed=[
                ResourceRequirement(
                    resource_id="mental-care-team",
                    quantity=1,
                    exclusive=mood_signal in {"distressed", "crisis"},
                )
            ],
        )

        return MentalCareSupportOutcome(
            decision_message=decision_message,
            feedback_event=feedback_event,
            care_intent=care_intent,
        )
