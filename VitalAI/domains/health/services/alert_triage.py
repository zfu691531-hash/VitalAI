"""首条 typed application flow 使用的健康预警分诊服务。"""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.domains.health.models import HealthAlertEntry, HealthAlertSnapshot
from VitalAI.domains.health.repositories import HealthAlertRepository
from VitalAI.platform.arbitration import Flexibility, GoalType, IntentDeclaration, ResourceRequirement
from VitalAI.platform.feedback import FeedbackEvent, FeedbackLayer
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary


@dataclass(slots=True)
class HealthTriageOutcome:
    """由健康预警 summary 生成的领域层结果。"""

    decision_message: MessageEnvelope
    feedback_event: FeedbackEvent
    escalation_intent: IntentDeclaration
    history_entry: HealthAlertEntry | None = None
    history_snapshot: HealthAlertSnapshot | None = None


@dataclass
class HealthAlertTriageService:
    """对高风险预警做出反应的最小健康领域服务。"""

    domain_agent_id: str = "health-domain-service"
    history_repository: HealthAlertRepository | None = None

    def triage(self, summary: EventSummary) -> HealthTriageOutcome:
        """把健康预警摘要转换成 typed 平台输出。"""
        risk_level = str(summary.payload.get("risk_level", "unknown"))
        user_id = str(summary.payload.get("user_id", "unknown-user"))

        # 同一个 summary 在这里被翻译成三类平台对象：
        # 决策消息、反馈事件、以及后续仲裁可消费的意图。
        decision_message = MessageEnvelope(
            from_agent=self.domain_agent_id,
            to_agent=summary.source_agent,
            trace_id=summary.trace_id,
            payload={
                "user_id": user_id,
                "decision": "dispatch_followup",
                "risk_level": risk_level,
            },
            msg_type="HEALTH_DECISION",
            priority=MessagePriority.HIGH if risk_level != "critical" else MessagePriority.CRITICAL,
            require_ack=True,
        )

        # feedback_event 让 reporting / observability 看见“这次领域处理已经闭环”。
        feedback_event = FeedbackEvent(
            trace_id=summary.trace_id,
            agent_id=self.domain_agent_id,
            task_id=summary.message_id,
            event_type="COMPLETED",
            feedback_layer=FeedbackLayer.L1,
            summary=f"Health alert triaged for {user_id} with risk {risk_level}",
            completion_rate=1.0,
            payload={
                "decision_message_id": decision_message.msg_id,
                "risk_level": risk_level,
            },
        )

        # escalation_intent 则把同一件事转成 arbitration 能理解的目标/资源表达。
        escalation_intent = IntentDeclaration(
            agent_id=self.domain_agent_id,
            action="arrange_health_followup",
            content_preview=f"Follow up on {user_id} risk={risk_level}",
            goal_type=GoalType.HEALTH,
            goal_weight=1.0 if risk_level == "critical" else 0.8,
            flexibility=Flexibility.FIXED if risk_level == "critical" else Flexibility.PREFERRED,
            resources_needed=[
                ResourceRequirement(
                    resource_id="care-team",
                    quantity=1,
                    exclusive=risk_level == "critical",
                )
            ],
        )

        history_entry = None
        history_snapshot = None
        if self.history_repository is not None:
            history_entry = self.history_repository.add_alert(
                user_id=user_id,
                risk_level=risk_level,
                source_agent=summary.source_agent,
                trace_id=summary.trace_id,
                message_id=summary.message_id,
            )
            history_snapshot = self.history_repository.get_snapshot(user_id=user_id)

        return HealthTriageOutcome(
            decision_message=decision_message,
            feedback_event=feedback_event,
            escalation_intent=escalation_intent,
            history_entry=history_entry,
            history_snapshot=history_snapshot,
        )

    def recall_history(self, *, user_id: str, limit: int = 20) -> HealthAlertSnapshot:
        """Load recent health alert history for one user."""
        if self.history_repository is None:
            return HealthAlertSnapshot(user_id=user_id)
        return self.history_repository.get_snapshot(user_id=user_id, limit=limit)
