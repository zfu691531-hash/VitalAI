"""Daily-life typed-flow domain service."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.domains.daily_life.models import DailyLifeCheckInEntry, DailyLifeCheckInSnapshot
from VitalAI.domains.daily_life.repositories import DailyLifeCheckInRepository
from VitalAI.platform.arbitration import Flexibility, GoalType, IntentDeclaration, ResourceRequirement
from VitalAI.platform.feedback import FeedbackEvent, FeedbackLayer
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary


@dataclass(slots=True)
class DailyLifeSupportOutcome:
    """Domain result generated from one daily-life check-in summary."""

    decision_message: MessageEnvelope
    feedback_event: FeedbackEvent
    support_intent: IntentDeclaration
    history_entry: DailyLifeCheckInEntry | None = None
    history_snapshot: DailyLifeCheckInSnapshot | None = None


@dataclass
class DailyLifeCheckInSupportService:
    """Minimal domain service for daily-life support check-ins."""

    domain_agent_id: str = "daily-life-domain-service"
    history_repository: DailyLifeCheckInRepository | None = None

    def support(self, summary: EventSummary) -> DailyLifeSupportOutcome:
        """Translate a daily-life check-in summary into typed platform outputs."""
        user_id = str(summary.payload.get("user_id", "unknown-user"))
        need = str(summary.payload.get("need", "general_support"))
        urgency = str(summary.payload.get("urgency", "normal"))

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

        history_entry = None
        history_snapshot = None
        if self.history_repository is not None:
            history_entry = self.history_repository.add_checkin(
                user_id=user_id,
                need=need,
                urgency=urgency,
                source_agent=summary.source_agent,
                trace_id=summary.trace_id,
                message_id=summary.message_id,
            )
            history_snapshot = self.history_repository.get_snapshot(user_id=user_id)

        return DailyLifeSupportOutcome(
            decision_message=decision_message,
            feedback_event=feedback_event,
            support_intent=support_intent,
            history_entry=history_entry,
            history_snapshot=history_snapshot,
        )

    def recall_history(self, *, user_id: str, limit: int = 20) -> DailyLifeCheckInSnapshot:
        """Load recent daily-life check-in history for one user."""
        if self.history_repository is None:
            return DailyLifeCheckInSnapshot(user_id=user_id)
        return self.history_repository.get_snapshot(user_id=user_id, limit=limit)
