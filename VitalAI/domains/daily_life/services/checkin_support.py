"""第二条 typed application flow 使用的日常生活支持服务。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.arbitration import Flexibility, GoalType, IntentDeclaration, ResourceRequirement
from VitalAI.platform.feedback import FeedbackEvent, FeedbackLayer
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary


@dataclass(slots=True)
class DailyLifeSupportOutcome:
    """由日常生活签到 summary 生成的领域层结果。"""

    decision_message: MessageEnvelope
    feedback_event: FeedbackEvent
    support_intent: IntentDeclaration


@dataclass
class DailyLifeCheckInSupportService:
    """对需要支持的签到做出反应的最小日常生活领域服务。"""

    domain_agent_id: str = "daily-life-domain-service"

    def support(self, summary: EventSummary) -> DailyLifeSupportOutcome:
        """把日常生活签到摘要转换成 typed 平台输出。"""
        user_id = str(summary.payload.get("user_id", "unknown-user"))
        need = str(summary.payload.get("need", "general_support"))
        urgency = str(summary.payload.get("urgency", "normal"))

        # 和 health triage 保持一致：把 summary 一次翻译成 decision / feedback / intent，
        # 避免后续链路分别重复理解 daily_life 语义。
        decision_message = MessageEnvelope(
            from_agent=self.domain_agent_id,
            to_agent=summary.source_agent,
            trace_id=summary.trace_id,
            payload={
                "user_id": user_id,
                "decision": "arrange_daily_life_support",
                "need": need,
                "urgency": urgency,
            },
            msg_type="DAILY_LIFE_DECISION",
            priority=MessagePriority.CRITICAL if urgency == "high" else MessagePriority.HIGH,
            require_ack=True,
        )

        # feedback_event 让 daily_life 这条流也能自然进入统一 reporting 入口。
        feedback_event = FeedbackEvent(
            trace_id=summary.trace_id,
            agent_id=self.domain_agent_id,
            task_id=summary.message_id,
            event_type="COMPLETED",
            feedback_layer=FeedbackLayer.L1,
            summary=f"Daily life support triaged for {user_id} need={need}",
            completion_rate=1.0,
            payload={
                "decision_message_id": decision_message.msg_id,
                "need": need,
                "urgency": urgency,
            },
        )

        # support_intent 留给后续资源协调/仲裁层消费，而不是只停留在领域内部。
        support_intent = IntentDeclaration(
            agent_id=self.domain_agent_id,
            action="coordinate_daily_life_support",
            content_preview=f"Support {user_id} with need={need}",
            goal_type=GoalType.DAILY_LIFE,
            goal_weight=0.9 if urgency == "high" else 0.7,
            flexibility=Flexibility.FIXED if urgency == "high" else Flexibility.PREFERRED,
            resources_needed=[
                ResourceRequirement(
                    resource_id="daily-life-team",
                    quantity=1,
                    exclusive=urgency == "high",
                )
            ],
        )

        return DailyLifeSupportOutcome(
            decision_message=decision_message,
            feedback_event=feedback_event,
            support_intent=support_intent,
        )
