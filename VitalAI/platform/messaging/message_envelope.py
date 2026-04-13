"""Cross-agent messaging contracts for the platform layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4


class MessagePriority(StrEnum):
    """Supported message priorities for intra-platform delivery."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class MessageEnvelope:
    """Standard message envelope shared by platform components and agents."""

    from_agent: str
    to_agent: str
    payload: dict[str, Any]
    msg_id: str = field(default_factory=lambda: uuid4().hex)
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    reply_to: str | None = None
    priority: MessagePriority = MessagePriority.NORMAL
    msg_type: str = "EVENT"
    version: str = "v1"
    ttl: int | None = None
    require_ack: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    expire_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.expire_at is None and self.ttl is not None:
            self.expire_at = self.timestamp + timedelta(seconds=self.ttl)

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the message is already outside its delivery window."""
        if self.expire_at is None:
            return False
        current = now or datetime.now(UTC)
        return current >= self.expire_at

    def can_reply(self) -> bool:
        """Return whether the current envelope can be used as a reply target."""
        return not self.is_expired()
