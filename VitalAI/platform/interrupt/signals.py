"""Interrupt contracts for platform emergency handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class InterruptPriority(StrEnum):
    """P0-P3 interrupt priority ladder."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class InterruptAction(StrEnum):
    """Minimal runtime actions triggered by an interrupt."""

    PAUSE = "PAUSE"
    RESUME = "RESUME"
    CANCEL = "CANCEL"
    TAKEOVER = "TAKEOVER"
    ESCALATE = "ESCALATE"


@dataclass(slots=True)
class SnapshotReference:
    """Reference to the runtime snapshot needed for recovery or takeover."""

    snapshot_id: str
    source: str
    captured_at: datetime | None = None
    version: int | None = None


@dataclass(slots=True)
class InterruptSignal:
    """Typed interrupt input consumed by runtime coordination components."""

    trace_id: str
    source: str
    priority: InterruptPriority
    action: InterruptAction
    reason: str
    signal_id: str = field(default_factory=lambda: uuid4().hex)
    target: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    snapshot_refs: list[SnapshotReference] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def needs_interrupt_snapshot(self) -> bool:
        """Return whether the signal should carry snapshot references."""
        return self.priority in {InterruptPriority.P0, InterruptPriority.P1} or self.action in {
            InterruptAction.TAKEOVER,
            InterruptAction.RESUME,
        }

    def has_snapshot_refs(self) -> bool:
        """Return whether recovery material is attached."""
        return bool(self.snapshot_refs)
