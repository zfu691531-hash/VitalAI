"""Thin consumer adapters for the current typed application flows."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application import DailyLifeCheckInCommand, HealthAlertCommand
from VitalAI.interfaces.typed_flow_support import (
    get_consumer_application_assembly,
    serialize_workflow_result,
)


@dataclass(slots=True)
class HealthAlertConsumedEvent:
    """Consumed event payload for the health flow."""

    source_agent: str
    trace_id: str
    user_id: str
    risk_level: str


@dataclass(slots=True)
class DailyLifeCheckInConsumedEvent:
    """Consumed event payload for the daily life flow."""

    source_agent: str
    trace_id: str
    user_id: str
    need: str
    urgency: str = "normal"


def consume_health_alert(event: HealthAlertConsumedEvent) -> dict[str, object]:
    """Consume a health-alert style event and dispatch the health workflow."""
    workflow = get_consumer_application_assembly().build_health_workflow()
    result = workflow.run(
        HealthAlertCommand(
            source_agent=event.source_agent,
            trace_id=event.trace_id,
            user_id=event.user_id,
            risk_level=event.risk_level,
        )
    )
    return serialize_workflow_result(result)


def consume_daily_life_checkin(event: DailyLifeCheckInConsumedEvent) -> dict[str, object]:
    """Consume a daily-life event and dispatch the daily-life workflow."""
    workflow = get_consumer_application_assembly().build_daily_life_workflow()
    result = workflow.run(
        DailyLifeCheckInCommand(
            source_agent=event.source_agent,
            trace_id=event.trace_id,
            user_id=event.user_id,
            need=event.need,
            urgency=event.urgency,
        )
    )
    return serialize_workflow_result(result)
