"""Feedback contracts for the platform feedback loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class FeedbackLayer(StrEnum):
    """Feedback loop layers aligned with the current architecture."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


@dataclass(slots=True)
class FailureDetails:
    """Optional failure metadata carried by a feedback event."""

    error_code: str
    message: str
    retryable: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FeedbackEvent:
    """Typed feedback event emitted by agents or runtime components."""

    trace_id: str
    agent_id: str
    task_id: str
    event_type: str
    feedback_layer: FeedbackLayer
    summary: str
    event_id: str = field(default_factory=lambda: uuid4().hex)
    confidence_score: float | None = None
    quality_score: float | None = None
    completion_rate: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    failure: FailureDetails | None = None

    def is_failure(self) -> bool:
        """Return whether this feedback event carries failure information."""
        return self.failure is not None

    def is_terminal(self) -> bool:
        """Return whether the feedback marks an end-of-task state."""
        terminal_types = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT"}
        return self.event_type.upper() in terminal_types
