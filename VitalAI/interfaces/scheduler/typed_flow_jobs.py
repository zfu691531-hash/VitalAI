"""Thin scheduler adapters for the current typed application flows."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.application import DailyLifeCheckInCommand, HealthAlertCommand
from VitalAI.interfaces.typed_flow_support import (
    get_scheduler_application_assembly,
    serialize_workflow_result,
)


@dataclass(slots=True)
class ScheduledHealthAlertJob:
    """Scheduled health alert input."""

    source_agent: str
    trace_id: str
    user_id: str
    risk_level: str


@dataclass(slots=True)
class ScheduledDailyLifeCheckInJob:
    """Scheduled daily life check-in input."""

    source_agent: str
    trace_id: str
    user_id: str
    need: str
    urgency: str = "normal"


def run_scheduled_health_alert(job: ScheduledHealthAlertJob) -> dict[str, object]:
    """Execute the health workflow from a scheduler-style entrypoint."""
    workflow = get_scheduler_application_assembly().build_health_workflow()
    result = workflow.run(
        HealthAlertCommand(
            source_agent=job.source_agent,
            trace_id=job.trace_id,
            user_id=job.user_id,
            risk_level=job.risk_level,
        )
    )
    return serialize_workflow_result(result)


def run_scheduled_daily_life_checkin(job: ScheduledDailyLifeCheckInJob) -> dict[str, object]:
    """Execute the daily-life workflow from a scheduler-style entrypoint."""
    workflow = get_scheduler_application_assembly().build_daily_life_workflow()
    result = workflow.run(
        DailyLifeCheckInCommand(
            source_agent=job.source_agent,
            trace_id=job.trace_id,
            user_id=job.user_id,
            need=job.need,
            urgency=job.urgency,
        )
    )
    return serialize_workflow_result(result)
