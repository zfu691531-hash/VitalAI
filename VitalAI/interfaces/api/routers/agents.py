"""HTTP adapters for the lightweight agent registry and dry-run APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from VitalAI.interfaces.agent_support import (
    get_agent_descriptor,
    list_agent_descriptors,
    run_agent_dry_run,
)

router = APIRouter()


@dataclass(slots=True)
class AgentDryRunRequest:
    """Permissive request model used to preview one agent through the registry."""

    source_agent: Any = "agent-registry-api"
    trace_id: Any = ""
    user_id: Any = ""
    channel: Any = ""
    message: Any = ""
    event_type: Any = ""
    operation: Any = ""
    context: Any = field(default_factory=dict)
    payload: Any = field(default_factory=dict)
    tool_name: Any = ""
    params: Any = field(default_factory=dict)
    text: Any = ""
    history_limit: Any = 3
    memory_key: Any = ""


def list_agents(role: str = "api") -> dict[str, object]:
    """Return all registered agents for one runtime role."""
    agents = list_agent_descriptors(role=role)
    return {
        "role": role,
        "count": len(agents),
        "agents": agents,
    }


def get_agent(agent_id: str, role: str = "api") -> dict[str, object]:
    """Return one registered agent descriptor."""
    try:
        descriptor = get_agent_descriptor(agent_id, role=role)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "agent_not_found", "agent_id": agent_id, "role": role},
        ) from exc
    return {"role": role, "agent": descriptor}


def preview_agent(agent_id: str, request: AgentDryRunRequest, role: str = "api") -> dict[str, object]:
    """Run one agent dry-run through the registry."""
    payload = {
        "source_agent": _request_text(request.source_agent, "agent-registry-api"),
        "trace_id": _request_text(request.trace_id, ""),
        "user_id": _request_text(request.user_id, ""),
        "channel": _request_text(request.channel, ""),
        "message": _request_text(request.message, ""),
        "event_type": _request_text(request.event_type, ""),
        "operation": _request_text(request.operation, ""),
        "context": request.context if isinstance(request.context, dict) else {},
        "payload": request.payload if isinstance(request.payload, dict) else {},
        "tool_name": _request_text(request.tool_name, ""),
        "params": request.params if isinstance(request.params, dict) else {},
        "text": _request_text(request.text, ""),
        "history_limit": request.history_limit,
        "memory_key": _request_text(request.memory_key, ""),
    }
    try:
        result = run_agent_dry_run(agent_id, payload, role=role)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "agent_not_found", "agent_id": agent_id, "role": role},
        ) from exc
    return {"role": role, "dry_run": result}


@router.get("/agents")
def list_agents_endpoint(role: str = Query(default="api")) -> dict[str, object]:
    """HTTP entrypoint for the registered agent list."""
    return list_agents(role=role)


@router.get("/agents/{agent_id}")
def get_agent_endpoint(agent_id: str, role: str = Query(default="api")) -> dict[str, object]:
    """HTTP entrypoint for one registered agent descriptor."""
    return get_agent(agent_id, role=role)


@router.post("/agents/{agent_id}/dry-run")
def preview_agent_endpoint(
    agent_id: str,
    request: AgentDryRunRequest,
    role: str = Query(default="api"),
) -> dict[str, object]:
    """HTTP entrypoint for one agent dry-run."""
    return preview_agent(agent_id, request, role=role)


def _request_text(value: object, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text
