"""Degradation runtime policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from VitalAI.platform.interrupt import InterruptPriority, InterruptSignal


class DegradationLevel(StrEnum):
    """System degradation levels."""

    NORMAL = "NORMAL"
    ALERT = "ALERT"
    DEGRADED = "DEGRADED"
    SURVIVAL = "SURVIVAL"


@dataclass
class AutonomyRule:
    """Module autonomy rule used during degraded operation."""

    module_name: str
    description: str
    max_duration_minutes: int | None = None


@dataclass
class DegradationPolicy:
    """Minimal degradation policy set with interrupt-aware level mapping."""

    level: DegradationLevel = DegradationLevel.NORMAL
    autonomy_rules: list[AutonomyRule] = field(default_factory=list)

    def set_level(self, level: DegradationLevel) -> None:
        """Update the active degradation level."""
        self.level = level

    def add_rule(self, rule: AutonomyRule) -> None:
        """Append a new autonomy rule."""
        self.autonomy_rules.append(rule)

    def apply_interrupt(self, signal: InterruptSignal) -> DegradationLevel:
        """Map interrupt priority to a degradation level and apply it."""
        mapping = {
            InterruptPriority.P0: DegradationLevel.SURVIVAL,
            InterruptPriority.P1: DegradationLevel.DEGRADED,
            InterruptPriority.P2: DegradationLevel.ALERT,
            InterruptPriority.P3: DegradationLevel.NORMAL,
        }
        self.level = mapping[signal.priority]
        return self.level
