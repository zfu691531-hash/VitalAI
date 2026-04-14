"""当前 typed application flows 使用的薄 API 适配层。"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from VitalAI.application import (
    DailyLifeCheckInCommand,
    HealthAlertCommand,
    MentalCareCheckInCommand,
)
from VitalAI.interfaces.typed_flow_support import (
    build_policy_observation,
    get_api_application_assembly,
    get_application_health_failover_drill,
    get_application_policy_matrix,
    get_application_policy_snapshot,
    get_application_runtime_diagnostics,
    serialize_observation_record,
    serialize_policy_snapshot,
    serialize_runtime_diagnostics,
    serialize_workflow_result,
)

router = APIRouter()


@dataclass(slots=True)
class HealthAlertRequest:
    """健康预警的 API 请求模型。"""

    source_agent: str
    trace_id: str
    user_id: str
    risk_level: str


@dataclass(slots=True)
class DailyLifeCheckInRequest:
    """日常生活签到的 API 请求模型。"""

    source_agent: str
    trace_id: str
    user_id: str
    need: str
    urgency: str = "normal"


@dataclass(slots=True)
class MentalCareCheckInRequest:
    """精神关怀签到的 API 请求模型。"""

    source_agent: str
    trace_id: str
    user_id: str
    mood_signal: str
    support_need: str = "companionship"


def run_health_alert(request: HealthAlertRequest) -> dict[str, object]:
    """执行健康预警 workflow，并返回响应形状的字典。"""
    workflow = get_api_application_assembly().build_health_workflow()
    result = workflow.run(
        HealthAlertCommand(
            source_agent=request.source_agent,
            trace_id=request.trace_id,
            user_id=request.user_id,
            risk_level=request.risk_level,
        )
    )
    return serialize_workflow_result(result)


def run_daily_life_checkin(request: DailyLifeCheckInRequest) -> dict[str, object]:
    """执行日常生活签到 workflow，并返回响应形状的字典。"""
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
    return serialize_workflow_result(result)


def run_mental_care_checkin(request: MentalCareCheckInRequest) -> dict[str, object]:
    """执行精神关怀签到 workflow，并返回响应形状的字典。"""
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
    return serialize_workflow_result(result)


def get_runtime_policy(role: str = "api") -> dict[str, object]:
    """返回某个运行角色当前的 application assembly 策略快照。"""
    return serialize_policy_snapshot(get_application_policy_snapshot(role))


def get_runtime_policy_matrix() -> dict[str, dict[str, object]]:
    """返回所有标准角色当前的 application assembly 策略矩阵。"""
    return get_application_policy_matrix()


def get_runtime_policy_observation(role: str = "api") -> dict[str, object]:
    """返回某个角色策略快照对应的观测记录。"""
    return serialize_observation_record(build_policy_observation(role))


def get_runtime_diagnostics(role: str = "api") -> dict[str, object]:
    """Return runtime diagnostics for one role."""
    return serialize_runtime_diagnostics(get_application_runtime_diagnostics(role))


def get_health_failover_drill(role: str = "api") -> dict[str, object]:
    """Return a controlled health-critical failover drill for one role."""
    return serialize_runtime_diagnostics(get_application_health_failover_drill(role))


@router.post("/flows/health-alert")
def health_alert_endpoint(request: HealthAlertRequest) -> dict[str, object]:
    """当前 typed 健康预警流的 HTTP 入口。"""
    return run_health_alert(request)


@router.post("/flows/daily-life-checkin")
def daily_life_checkin_endpoint(request: DailyLifeCheckInRequest) -> dict[str, object]:
    """当前 typed 日常生活流的 HTTP 入口。"""
    return run_daily_life_checkin(request)


@router.post("/flows/mental-care-checkin")
def mental_care_checkin_endpoint(request: MentalCareCheckInRequest) -> dict[str, object]:
    """当前 typed 精神关怀流的 HTTP 入口。"""
    return run_mental_care_checkin(request)


@router.get("/flows/policies/{role}")
def runtime_policy_endpoint(role: str) -> dict[str, object]:
    """查看当前 typed-flow 策略快照的 HTTP 入口。"""
    return get_runtime_policy(role)


@router.get("/flows/policies/{role}/observation")
def runtime_policy_observation_endpoint(role: str) -> dict[str, object]:
    """查看某个角色策略快照观测记录的 HTTP 入口。"""
    return get_runtime_policy_observation(role)


@router.get("/flows/runtime-diagnostics/{role}")
def runtime_diagnostics_endpoint(role: str) -> dict[str, object]:
    """Return runtime diagnostics for one role."""
    return get_runtime_diagnostics(role)


@router.get("/flows/runtime-diagnostics/{role}/health-failover")
def health_failover_drill_endpoint(role: str) -> dict[str, object]:
    """Return a controlled health-critical failover drill for one role."""
    return get_health_failover_drill(role)


@router.get("/flows/policies")
def runtime_policy_matrix_endpoint() -> dict[str, dict[str, object]]:
    """查看标准 typed-flow 策略矩阵的 HTTP 入口。"""
    return get_runtime_policy_matrix()
