"""Typed command for minimal backend-only user interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class UserInteractionEventType(str, Enum):
    """Supported backend-only interaction event types."""

    HEALTH_ALERT = "health_alert"
    DAILY_LIFE_CHECKIN = "daily_life_checkin"
    MENTAL_CARE_CHECKIN = "mental_care_checkin"
    PROFILE_MEMORY_UPDATE = "profile_memory_update"
    PROFILE_MEMORY_QUERY = "profile_memory_query"


_EVENT_TYPE_ALIASES: dict[str, UserInteractionEventType] = {
    "health": UserInteractionEventType.HEALTH_ALERT,
    "health_alert": UserInteractionEventType.HEALTH_ALERT,
    "daily_life": UserInteractionEventType.DAILY_LIFE_CHECKIN,
    "daily_life_checkin": UserInteractionEventType.DAILY_LIFE_CHECKIN,
    "mental_care": UserInteractionEventType.MENTAL_CARE_CHECKIN,
    "mental_care_checkin": UserInteractionEventType.MENTAL_CARE_CHECKIN,
    "profile_memory": UserInteractionEventType.PROFILE_MEMORY_UPDATE,
    "profile_memory_update": UserInteractionEventType.PROFILE_MEMORY_UPDATE,
    "remember": UserInteractionEventType.PROFILE_MEMORY_UPDATE,
    "memory_update": UserInteractionEventType.PROFILE_MEMORY_UPDATE,
    "profile_memory_snapshot": UserInteractionEventType.PROFILE_MEMORY_QUERY,
    "profile_memory_query": UserInteractionEventType.PROFILE_MEMORY_QUERY,
    "profile_memory_read": UserInteractionEventType.PROFILE_MEMORY_QUERY,
    "recall": UserInteractionEventType.PROFILE_MEMORY_QUERY,
}


@dataclass(frozen=True, slots=True)
class UserInteractionSessionContext:
    """Minimal backend-only session context without multi-turn chat state."""

    session_id: str
    user_id: str
    channel: str


@dataclass(slots=True)
class UserInteractionCommand:
    """Application command representing one user-facing interaction."""

    user_id: str
    channel: str
    message: str
    event_type: str = ""
    context: object = field(default_factory=dict)
    trace_id: str = ""
    source_agent: str = "user-interaction-api"

    def validation_issues(self) -> list[dict[str, str]]:
        """Return request-level validation issues before workflow routing."""
        issues: list[dict[str, str]] = []
        if not self.user_id.strip():
            issues.append({"field": "user_id", "code": "required"})
        if not self.channel.strip():
            issues.append({"field": "channel", "code": "required"})
        if not self.message.strip():
            issues.append({"field": "message", "code": "required"})
        if not isinstance(self.context, dict):
            issues.append({"field": "context", "code": "must_be_object"})
        return issues

    def resolved_event_type(self) -> UserInteractionEventType | None:
        """Return the normalized supported interaction event type, if any."""
        normalized = self.event_type.strip().lower().replace("-", "_").replace(" ", "_")
        return _EVENT_TYPE_ALIASES.get(normalized)

    def context_mapping(self) -> dict[str, object]:
        """Return the interaction context as a safe mapping."""
        if isinstance(self.context, dict):
            return self.context
        return {}

    def resolved_session_context(self) -> UserInteractionSessionContext:
        """Return the minimal session context for this backend-only interaction."""
        context = self.context_mapping()
        raw_session_id = context.get("session_id")
        session_id = "" if raw_session_id is None else str(raw_session_id).strip()
        if not session_id:
            session_id = f"{self.user_id.strip()}:{self.channel.strip()}"
        return UserInteractionSessionContext(
            session_id=session_id,
            user_id=self.user_id.strip(),
            channel=self.channel.strip(),
        )

    def resolved_trace_id(self) -> str:
        """Return a stable trace id for this interaction."""
        if self.trace_id.strip():
            return self.trace_id
        return f"interaction-{uuid4().hex}"

    def resolved_source_agent(self) -> str:
        """Return the source agent recorded in downstream flow commands."""
        if self.source_agent.strip():
            return self.source_agent
        return f"interaction-{self.channel}"


def supported_user_interaction_event_types() -> list[str]:
    """Return supported canonical event type values."""
    return [event_type.value for event_type in UserInteractionEventType]


def required_context_fields_for_event_type(
    event_type: UserInteractionEventType,
) -> tuple[str, ...]:
    """Return explicit context fields required by one event type."""
    if event_type is UserInteractionEventType.PROFILE_MEMORY_UPDATE:
        return ("memory_key", "memory_value")
    return ()


def missing_context_fields(
    context: dict[str, Any],
    event_type: UserInteractionEventType,
) -> list[str]:
    """Return required context fields that are missing or blank."""
    missing: list[str] = []
    for field_name in required_context_fields_for_event_type(event_type):
        value = context.get(field_name)
        if value is None or str(value).strip() == "":
            missing.append(field_name)
    return missing
