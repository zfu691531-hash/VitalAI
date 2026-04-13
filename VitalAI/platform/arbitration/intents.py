"""Intent declaration contracts for arbitration inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class GoalType(StrEnum):
    """High-level goal categories used by arbitration."""

    SAFETY = "SAFETY"
    HEALTH = "HEALTH"
    DAILY_LIFE = "DAILY_LIFE"
    MENTAL_CARE = "MENTAL_CARE"
    REPORTING = "REPORTING"
    SYSTEM = "SYSTEM"


class Flexibility(StrEnum):
    """How much the requested target time or outcome may shift."""

    FIXED = "FIXED"
    PREFERRED = "PREFERRED"
    FLEXIBLE = "FLEXIBLE"


@dataclass(slots=True)
class ResourceRequirement:
    """Minimal resource declaration attached to an intent."""

    resource_id: str
    quantity: int = 1
    exclusive: bool = False


@dataclass(slots=True)
class IntentDeclaration:
    """Standard arbitration contract submitted by agents or workflows."""

    agent_id: str
    action: str
    content_preview: str
    goal_type: GoalType
    goal_weight: float
    flexibility: Flexibility
    intent_id: str = field(default_factory=lambda: uuid4().hex)
    submit_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    target_time: datetime | None = None
    resources_needed: list[ResourceRequirement] = field(default_factory=list)

    def requires_exclusive_resources(self) -> bool:
        """Return whether the intent claims any exclusive resource."""
        return any(resource.exclusive for resource in self.resources_needed)

    def is_time_sensitive(self) -> bool:
        """Return whether the intent carries an explicit execution target."""
        return self.target_time is not None
