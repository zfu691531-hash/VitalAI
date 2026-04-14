"""Event Aggregator runtime shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from VitalAI.platform.messaging import MessageEnvelope, MessagePriority

if TYPE_CHECKING:
    from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass(slots=True)
class EventSummary:
    """Structured event summary forwarded to the decision core."""

    message_id: str
    trace_id: str
    event_type: str
    source_agent: str
    target_agent: str
    priority: MessagePriority
    timestamp: datetime
    payload: dict[str, object]


@dataclass
class EventAggregator:
    """Minimal aggregator that stores valid envelopes and emits summaries."""

    raw_events: list[MessageEnvelope] = field(default_factory=list)

    def ingest(self, event: MessageEnvelope) -> bool:
        """Accept a message envelope unless it has already expired."""
        if event.is_expired():
            return False
        self.raw_events.append(event)
        return True

    def summarize(self, signal_bridge: "RuntimeSignalBridge | None" = None) -> list[EventSummary]:
        """Convert buffered envelopes into structured event summaries."""
        summaries = [
            EventSummary(
                message_id=event.msg_id,
                trace_id=event.trace_id,
                event_type=event.msg_type,
                source_agent=event.from_agent,
                target_agent=event.to_agent,
                priority=event.priority,
                timestamp=event.timestamp.astimezone(UTC),
                payload=dict(event.payload),
            )
            for event in self.raw_events
        ]
        if signal_bridge is not None:
            for summary in summaries:
                signal_bridge.observe_event_summary(summary)
        return summaries
