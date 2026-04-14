"""Decision Core runtime shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.runtime.event_aggregator import EventSummary


DecisionHandler = Callable[[EventSummary], MessageEnvelope | None]


@dataclass
class DecisionCore:
    """Minimal decision core that dispatches typed summaries to handlers."""

    handlers: dict[str, DecisionHandler] = field(default_factory=dict)

    def register_handler(self, event_type: str, handler: DecisionHandler) -> None:
        """Register a handler for a summarized event type."""
        self.handlers[event_type] = handler

    def process_summary(self, summary: EventSummary) -> MessageEnvelope | None:
        """Process a summary and return an optional outbound message."""
        handler = self.handlers.get(summary.event_type)
        if handler is None:
            return None
        return handler(summary)
