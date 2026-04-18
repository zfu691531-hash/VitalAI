"""HTTP adapter for minimal backend-only user interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Query

from VitalAI.application import UserInteractionCommand, UserOverviewQuery
from VitalAI.interfaces.agent_support import serialize_agent_dry_run_result
from VitalAI.interfaces.typed_flow_support import (
    build_intelligent_reporting_agent,
    build_user_interaction_workflow,
    build_user_overview_query_workflow,
    serialize_user_interaction_result,
    serialize_user_overview_query_result,
)

router = APIRouter()


@dataclass(slots=True)
class UserInteractionRequest:
    """API request model for one minimal user interaction."""

    user_id: Any = ""
    channel: Any = ""
    message: Any = ""
    event_type: Any = ""
    context: Any = field(default_factory=dict)
    trace_id: Any = ""
    source_agent: Any = "user-interaction-api"


def run_user_interaction(request: UserInteractionRequest) -> dict[str, object]:
    """Execute one backend-only user interaction and serialize the response."""
    workflow = build_user_interaction_workflow(role="api")
    result = workflow.run(
        UserInteractionCommand(
            user_id=_request_text(request.user_id),
            channel=_request_text(request.channel),
            message=_request_text(request.message),
            event_type=_request_text(request.event_type),
            context=request.context,
            trace_id=_request_text(request.trace_id),
            source_agent=_request_text(request.source_agent),
        )
    )
    return serialize_user_interaction_result(result)


def get_user_overview(
    user_id: str,
    *,
    source_agent: str = "user-overview-api",
    trace_id: str = "user-overview-query",
    history_limit: int = 3,
    memory_key: str = "",
) -> dict[str, object]:
    """Load a lightweight cross-domain overview for one user."""
    workflow = build_user_overview_query_workflow(role="api")
    result = workflow.run(
        UserOverviewQuery(
            source_agent=source_agent,
            trace_id=trace_id,
            user_id=user_id,
            history_limit=history_limit,
            memory_key=memory_key,
        )
    )
    return serialize_user_overview_query_result(result)


def get_user_report_preview(
    user_id: str,
    *,
    source_agent: str = "user-report-preview-api",
    trace_id: str = "user-report-preview",
    history_limit: int = 3,
    memory_key: str = "",
) -> dict[str, object]:
    """Load a read-only report preview for one user through the reporting agent."""
    agent = build_intelligent_reporting_agent(role="api")
    result = agent.generate_report_preview(
        user_id=user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        history_limit=history_limit,
        memory_key=memory_key,
    )
    return serialize_agent_dry_run_result(result)


@router.post("/interactions")
def user_interaction_endpoint(request: UserInteractionRequest) -> dict[str, object]:
    """HTTP entrypoint for backend-only user interactions."""
    return run_user_interaction(request)


@router.get("/users/{user_id}/overview")
def user_overview_endpoint(
    user_id: str,
    source_agent: str = "user-overview-api",
    trace_id: str = "user-overview-query",
    history_limit: int = Query(default=3, ge=1, le=20),
    memory_key: str = "",
) -> dict[str, object]:
    """HTTP entrypoint for one lightweight cross-domain user overview."""
    return get_user_overview(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        history_limit=history_limit,
        memory_key=memory_key,
    )


@router.get("/users/{user_id}/report-preview")
def user_report_preview_endpoint(
    user_id: str,
    source_agent: str = "user-report-preview-api",
    trace_id: str = "user-report-preview",
    history_limit: int = Query(default=3, ge=1, le=20),
    memory_key: str = "",
) -> dict[str, object]:
    """HTTP entrypoint for one read-only user report preview."""
    return get_user_report_preview(
        user_id,
        source_agent=source_agent,
        trace_id=trace_id,
        history_limit=history_limit,
        memory_key=memory_key,
    )


def _request_text(value: object) -> str:
    """Coerce permissive API input into the application command contract."""
    if value is None:
        return ""
    return str(value)
