"""HTTP adapter for minimal backend-only user interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter

from VitalAI.application import UserInteractionCommand
from VitalAI.interfaces.typed_flow_support import (
    build_user_interaction_workflow,
    serialize_user_interaction_result,
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


@router.post("/interactions")
def user_interaction_endpoint(request: UserInteractionRequest) -> dict[str, object]:
    """HTTP entrypoint for backend-only user interactions."""
    return run_user_interaction(request)


def _request_text(value: object) -> str:
    """Coerce permissive API input into the application command contract."""
    if value is None:
        return ""
    return str(value)
