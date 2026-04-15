"""Domain service for profile-memory persistence flows."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.domains.profile_memory.models.profile_memory_entry import (
    ProfileMemoryEntry,
    ProfileMemorySnapshot,
)
from VitalAI.domains.profile_memory.repositories.profile_memory_repository import ProfileMemoryRepository
from VitalAI.platform.feedback import FeedbackEvent, FeedbackLayer
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.runtime.event_aggregator import EventSummary


@dataclass(slots=True)
class ProfileMemoryUpdateOutcome:
    """Typed domain result for a persisted profile-memory update."""

    stored_entry: ProfileMemoryEntry
    profile_snapshot: ProfileMemorySnapshot
    decision_message: MessageEnvelope
    feedback_event: FeedbackEvent


@dataclass(slots=True)
class ProfileMemoryQueryOutcome:
    """Typed domain result for a read-only profile-memory query."""

    profile_snapshot: ProfileMemorySnapshot


@dataclass
class ProfileMemoryUpdateService:
    """Persist and read back long-term profile-memory state."""

    repository: ProfileMemoryRepository
    domain_agent_id: str = "profile-memory-domain-service"

    def remember(self, summary: EventSummary) -> ProfileMemoryUpdateOutcome:
        """Persist one memory update and return a fresh profile snapshot."""
        user_id = str(summary.payload.get("user_id", "unknown-user"))
        memory_key = str(summary.payload.get("memory_key", "general_preference"))
        memory_value = str(summary.payload.get("memory_value", ""))

        stored_entry = self.repository.upsert_memory(
            user_id=user_id,
            memory_key=memory_key,
            memory_value=memory_value,
            source_agent=summary.source_agent,
            trace_id=summary.trace_id,
        )
        profile_snapshot = self.repository.get_snapshot(user_id=user_id)

        decision_message = MessageEnvelope(
            from_agent=self.domain_agent_id,
            to_agent=summary.source_agent,
            trace_id=summary.trace_id,
            payload={
                "user_id": user_id,
                "decision": "profile_memory_updated",
                "memory_key": memory_key,
                "memory_count": profile_snapshot.memory_count,
            },
            msg_type="PROFILE_MEMORY_DECISION",
            priority=MessagePriority.NORMAL,
            require_ack=False,
        )

        feedback_event = FeedbackEvent(
            trace_id=summary.trace_id,
            agent_id=self.domain_agent_id,
            task_id=summary.message_id,
            event_type="COMPLETED",
            feedback_layer=FeedbackLayer.L1,
            summary=f"Profile memory updated for {user_id} key={memory_key}",
            completion_rate=1.0,
            payload={
                "memory_key": memory_key,
                "memory_count": profile_snapshot.memory_count,
                "decision_message_id": decision_message.msg_id,
            },
        )

        return ProfileMemoryUpdateOutcome(
            stored_entry=stored_entry,
            profile_snapshot=profile_snapshot,
            decision_message=decision_message,
            feedback_event=feedback_event,
        )

    def recall_snapshot(self, *, user_id: str, memory_key: str = "") -> ProfileMemoryQueryOutcome:
        """Read the current profile-memory snapshot without mutating state."""
        return ProfileMemoryQueryOutcome(
            profile_snapshot=self.repository.get_snapshot(user_id=user_id, memory_key=memory_key),
        )
