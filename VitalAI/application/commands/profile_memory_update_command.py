"""Typed command used by the profile-memory update workflow."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.messaging import MessageEnvelope, MessagePriority


@dataclass(slots=True)
class ProfileMemoryUpdateCommand:
    """Application command for one long-term profile-memory update."""

    source_agent: str
    trace_id: str
    user_id: str
    memory_key: str
    memory_value: str
    target_agent: str = "decision-core"

    def to_message_envelope(self) -> MessageEnvelope:
        """Translate the command into the shared runtime ingress contract."""
        return MessageEnvelope(
            from_agent=self.source_agent,
            to_agent=self.target_agent,
            trace_id=self.trace_id,
            payload={
                "user_id": self.user_id,
                "memory_key": self.memory_key,
                "memory_value": self.memory_value,
            },
            msg_type="PROFILE_MEMORY_UPDATE",
            priority=MessagePriority.NORMAL,
            ttl=300,
            require_ack=True,
        )
