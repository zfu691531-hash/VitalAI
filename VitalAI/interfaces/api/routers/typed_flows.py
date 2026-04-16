"""Thin HTTP adapters for the current typed application flows."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, status

from VitalAI.application import (
    DailyLifeCheckInCommand,
    DailyLifeCheckInHistoryQuery,
    HealthAlertCommand,
    HealthAlertHistoryQuery,
    MentalCareCheckInCommand,
    MentalCareCheckInHistoryQuery,
    ProfileMemorySnapshotQuery,
    ProfileMemoryUpdateCommand,
)
from VitalAI.interfaces.api.admin_auth import require_admin_token
from VitalAI.interfaces.typed_flow_support import (
    build_policy_observation,
    get_api_application_assembly,
    get_application_health_failover_drill,
    get_application_policy_matrix,
    get_application_policy_snapshot,
    get_application_runtime_diagnostics,
    runtime_controls_enabled,
    serialize_observation_record,
    serialize_daily_life_query_result,
    serialize_daily_life_workflow_result,
    serialize_health_query_result,
    serialize_health_workflow_result,
    serialize_mental_care_query_result,
    serialize_mental_care_workflow_result,
    serialize_policy_snapshot,
    serialize_profile_memory_query_result,
    serialize_profile_memory_workflow_result,
    serialize_runtime_diagnostics,
    serialize_workflow_result,
)

router = APIRouter()


@dataclass(slots=True)
class HealthAlertRequest:
    """API request model for health alerts."""

    source_agent: str
    trace_id: str
    user_id: str
    risk_level: str


@dataclass(slots=True)
class DailyLifeCheckInRequest:
    """API request model for daily-life check-ins."""

    source_agent: str
    trace_id: str
    user_id: str
    need: str
    urgency: str = "normal"


@dataclass(slots=True)
class MentalCareCheckInRequest:
    """API request model for mental-care check-ins."""

    source_agent: str
    trace_id: str
    user_id: str
    mood_signal: str
    support_need: str = "companionship"


@dataclass(slots=True)
class ProfileMemoryUpdateRequest:
    """API request model for long-term profile-memory updates."""

    source_agent: str
    trace_id: str
    user_id: str
    memory_key: str
    memory_value: str


def run_health_alert(request: HealthAlertRequest) -> dict[str, object]:
    """Execute the health-alert workflow and serialize the response."""
    workflow = get_api_application_assembly().build_health_workflow()
    result = workflow.run(
        HealthAlertCommand(
            source_agent=request.source_agent,
            trace_id=request.trace_id,
            user_id=request.user_id,
            risk_level=request.risk_level,
        )
    )
    return serialize_health_workflow_result(result)


def get_health_alert_history(
    user_id: str,
    *,
    source_agent: str = "health-api",
    trace_id: str = "health-history-query",
    limit: int = 20,
) -> dict[str, object]:
    """Execute the health alert history read workflow and serialize the response."""
    workflow = get_api_application_assembly().build_health_alert_history_query_workflow()
    result = workflow.run(
        HealthAlertHistoryQuery(
            source_agent=source_agent,
            trace_id=trace_id,
            user_id=user_id,
            limit=limit,
        )
    )
    return serialize_health_query_result(result)


def run_daily_life_checkin(request: DailyLifeCheckInRequest) -> dict[str, object]:
    """Execute the daily-life workflow and serialize the response."""
    workflow = get_api_application_assembly().build_daily_life_workflow()
    result = workflow.run(
        DailyLifeCheckInCommand(
            source_agent=request.source_agent,
            trace_id=request.trace_id,
            user_id=request.user_id,
            need=request.need,
            urgency=request.urgency,
        )
    )
    return serialize_daily_life_workflow_result(result)


def run_mental_care_checkin(request: MentalCareCheckInRequest) -> dict[str, object]:
    """Execute the mental-care workflow and serialize the response."""
    workflow = get_api_application_assembly().build_mental_care_workflow()
    result = workflow.run(
        MentalCareCheckInCommand(
            source_agent=request.source_agent,
            trace_id=request.trace_id,
            user_id=request.user_id,
            mood_signal=request.mood_signal,
            support_need=request.support_need,
        )
    )
    return serialize_mental_care_workflow_result(result)


def get_mental_care_checkin_history(
    user_id: str,
    *,
    source_agent: str = "mental-care-api",
    trace_id: str = "mental-care-history-query",
    limit: int = 20,
) -> dict[str, object]:
    """Execute the mental-care history read workflow and serialize the response."""
    workflow = get_api_application_assembly().build_mental_care_checkin_history_query_workflow()
    result = workflow.run(
        MentalCareCheckInHistoryQuery(
            source_agent=source_agent,
            trace_id=trace_id,
            user_id=user_id,
            limit=limit,
        )
    )
    return serialize_mental_care_query_result(result)


def run_profile_memory_update(request: ProfileMemoryUpdateRequest) -> dict[str, object]:
    """Execute the profile-memory workflow and serialize the response."""
    workflow = get_api_application_assembly().build_profile_memory_workflow()
    result = workflow.run(
        ProfileMemoryUpdateCommand(
            source_agent=request.source_agent,
            trace_id=request.trace_id,
            user_id=request.user_id,
            memory_key=request.memory_key,
            memory_value=request.memory_value,
        )
    )
    return serialize_profile_memory_workflow_result(result)


def get_profile_memory_snapshot(
    user_id: str,
    *,
    source_agent: str = "profile-memory-api",
    trace_id: str = "profile-memory-query",
    memory_key: str = "",
) -> dict[str, object]:
    """Execute the profile-memory read workflow and serialize the response."""
    workflow = get_api_application_assembly().build_profile_memory_query_workflow()
    result = workflow.run(
        ProfileMemorySnapshotQuery(
            source_agent=source_agent,
            trace_id=trace_id,
            user_id=user_id,
            memory_key=memory_key,
        )
    )
    return serialize_profile_memory_query_result(result)


def get_daily_life_checkin_history(
    user_id: str,
    *,
    source_agent: str = "daily-life-api",
    trace_id: str = "daily-life-history-query",
    limit: int = 20,
) -> dict[str, object]:
    """Execute the daily-life history read workflow and serialize the response."""
    workflow = get_api_application_assembly().build_daily_life_checkin_history_query_workflow()
    result = workflow.run(
        DailyLifeCheckInHistoryQuery(
            source_agent=source_agent,
            trace_id=trace_id,
            user_id=user_id,
            limit=limit,
        )
    )
    return serialize_daily_life_query_result(result)


def get_runtime_policy(role: str = "api") -> dict[str, object]:
    """Return the current assembly policy snapshot for one role."""
    return serialize_policy_snapshot(get_application_policy_snapshot(role))


def get_runtime_policy_matrix() -> dict[str, dict[str, object]]:
    """Return policy snapshots for the standard runtime roles."""
    return get_application_policy_matrix()


def get_runtime_policy_observation(role: str = "api") -> dict[str, object]:
    """Return one policy observation record."""
    return serialize_observation_record(build_policy_observation(role))


def get_runtime_diagnostics(role: str = "api") -> dict[str, object]:
    """Return runtime diagnostics for one role."""
    return serialize_runtime_diagnostics(get_application_runtime_diagnostics(role))


def get_health_failover_drill(role: str = "api") -> dict[str, object]:
    """Return a controlled health-critical failover drill for one role."""
    return serialize_runtime_diagnostics(get_application_health_failover_drill(role))


def ensure_runtime_control_allowed(role: str = "api") -> None:
    """Guard side-effecting runtime control endpoints by environment policy."""
    if runtime_controls_enabled(role):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Runtime control endpoints are disabled for the current environment. "
            "Set VITALAI_RUNTIME_CONTROL_ENABLED=true to enable them explicitly."
        ),
    )


@router.post("/flows/health-alert")
def health_alert_endpoint(request: HealthAlertRequest) -> dict[str, object]:
    """HTTP entrypoint for the health-alert flow."""
    return run_health_alert(request)


@router.get("/flows/health-alerts/{user_id}")
def health_alert_history_endpoint(
    user_id: str,
    source_agent: str = Query(default="health-api"),
    trace_id: str = Query(default="health-history-query"),
    limit: int = Query(default=20),
) -> dict[str, object]:
    """HTTP entrypoint for read-only health alert history."""
    return get_health_alert_history(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        limit=limit,
    )


@router.post("/flows/daily-life-checkin")
def daily_life_checkin_endpoint(request: DailyLifeCheckInRequest) -> dict[str, object]:
    """HTTP entrypoint for the daily-life flow."""
    return run_daily_life_checkin(request)


@router.get("/flows/daily-life-checkins/{user_id}")
def daily_life_checkin_history_endpoint(
    user_id: str,
    source_agent: str = Query(default="daily-life-api"),
    trace_id: str = Query(default="daily-life-history-query"),
    limit: int = Query(default=20),
) -> dict[str, object]:
    """HTTP entrypoint for read-only daily-life check-in history."""
    return get_daily_life_checkin_history(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        limit=limit,
    )


@router.post("/flows/mental-care-checkin")
def mental_care_checkin_endpoint(request: MentalCareCheckInRequest) -> dict[str, object]:
    """HTTP entrypoint for the mental-care flow."""
    return run_mental_care_checkin(request)


@router.get("/flows/mental-care-checkins/{user_id}")
def mental_care_checkin_history_endpoint(
    user_id: str,
    source_agent: str = Query(default="mental-care-api"),
    trace_id: str = Query(default="mental-care-history-query"),
    limit: int = Query(default=20),
) -> dict[str, object]:
    """HTTP entrypoint for read-only mental-care check-in history."""
    return get_mental_care_checkin_history(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        limit=limit,
    )


@router.post("/flows/profile-memory")
def profile_memory_update_endpoint(request: ProfileMemoryUpdateRequest) -> dict[str, object]:
    """HTTP entrypoint for the profile-memory update flow."""
    return run_profile_memory_update(request)


@router.get("/flows/profile-memory/{user_id}")
def profile_memory_snapshot_endpoint(
    user_id: str,
    source_agent: str = Query(default="profile-memory-api"),
    trace_id: str = Query(default="profile-memory-query"),
    memory_key: str = Query(default=""),
) -> dict[str, object]:
    """HTTP entrypoint for a read-only profile-memory snapshot."""
    return get_profile_memory_snapshot(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        memory_key=memory_key,
    )


@router.get("/flows/policies/{role}")
def runtime_policy_endpoint(role: str) -> dict[str, object]:
    """HTTP entrypoint for one role policy snapshot."""
    return get_runtime_policy(role)


@router.get("/flows/policies/{role}/observation")
def runtime_policy_observation_endpoint(role: str) -> dict[str, object]:
    """HTTP entrypoint for one role policy observation."""
    return get_runtime_policy_observation(role)


@router.post("/admin/runtime-diagnostics/{role}")
def runtime_diagnostics_endpoint(
    role: str,
    _: None = Depends(require_admin_token),
) -> dict[str, object]:
    """HTTP entrypoint for side-effecting runtime diagnostics."""
    ensure_runtime_control_allowed(role)
    return get_runtime_diagnostics(role)


@router.post("/admin/runtime-diagnostics/{role}/health-failover")
def health_failover_drill_endpoint(
    role: str,
    _: None = Depends(require_admin_token),
) -> dict[str, object]:
    """HTTP entrypoint for the controlled health failover drill."""
    ensure_runtime_control_allowed(role)
    return get_health_failover_drill(role)


@router.get("/flows/policies")
def runtime_policy_matrix_endpoint() -> dict[str, dict[str, object]]:
    """HTTP entrypoint for the standard role policy matrix."""
    return get_runtime_policy_matrix()
