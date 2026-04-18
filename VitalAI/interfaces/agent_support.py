"""Shared agent registry and dry-run support for API adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from VitalAI.application.commands import UserInteractionCommand
from VitalAI.interfaces.typed_flow_support import (
    get_default_application_assembly,
    serialize_daily_life_workflow_result,
    serialize_health_workflow_result,
    serialize_mental_care_workflow_result,
    serialize_profile_memory_query_result,
    serialize_profile_memory_workflow_result,
)
from VitalAI.platform.agents import AgentDescriptor, AgentDryRunResult
from VitalAI.platform.messaging import MessageEnvelope


@dataclass(slots=True)
class _RegisteredAgent:
    """Internal helper that bundles one descriptor and its dry-run callable."""

    descriptor: AgentDescriptor
    run_dry_run: Callable[[dict[str, Any]], AgentDryRunResult]


def list_agent_descriptors(role: str = "api") -> list[dict[str, object]]:
    """Return all registered agents as serialized descriptors."""
    registry = _build_agent_registry(role)
    return [serialize_agent_descriptor(registry[agent_id].descriptor) for agent_id in _agent_order(registry)]


def get_agent_descriptor(agent_id: str, role: str = "api") -> dict[str, object]:
    """Return one serialized agent descriptor."""
    return serialize_agent_descriptor(_get_registered_agent(agent_id, role).descriptor)


def run_agent_dry_run(agent_id: str, payload: dict[str, Any], role: str = "api") -> dict[str, object]:
    """Execute one agent dry-run and serialize the result."""
    registered_agent = _get_registered_agent(agent_id, role)
    return serialize_agent_dry_run_result(registered_agent.run_dry_run(dict(payload)))


def serialize_agent_descriptor(descriptor: AgentDescriptor) -> dict[str, object]:
    """Serialize one agent descriptor for HTTP responses."""
    return {
        "agent_id": descriptor.agent_id,
        "display_name": descriptor.display_name,
        "layer": descriptor.layer,
        "domain": descriptor.domain,
        "status": descriptor.status,
        "summary": descriptor.summary,
        "execution_mode": descriptor.execution_mode,
        "mutates_state": descriptor.mutates_state,
        "accepts": list(descriptor.accepts),
        "emits": list(descriptor.emits),
        "platform_bindings": list(descriptor.platform_bindings),
    }


def serialize_agent_dry_run_result(result: AgentDryRunResult) -> dict[str, object]:
    """Serialize one dry-run result for HTTP responses."""
    return {
        "agent_id": result.agent_id,
        "accepted": result.accepted,
        "summary": result.summary,
        "execution_mode": result.execution_mode,
        "preview": dict(result.preview),
        "envelope": None if result.envelope is None else _serialize_message_envelope(result.envelope),
        "cycle": None if result.cycle is None else asdict(result.cycle),
        "findings": list(result.findings),
        "notes": list(result.notes),
    }


def _build_agent_registry(role: str) -> dict[str, _RegisteredAgent]:
    assembly = get_default_application_assembly(role=role)
    dispatch_use_case = assembly.build_domain_agent_dispatch_use_case()
    tool_agent = assembly.build_tool_agent()
    privacy_agent = assembly.build_privacy_guardian_agent()
    reporting_agent = assembly.build_intelligent_reporting_agent(
        tool_agent=tool_agent,
        privacy_guardian_agent=privacy_agent,
    )

    health_descriptor = AgentDescriptor(
        agent_id=dispatch_use_case.health_agent.agent_id,
        display_name="Health Domain Agent",
        layer="domain",
        domain="health",
        status="framework_ready",
        summary="承接健康告警与健康相关的领域决策，已接到主交互链路。",
        execution_mode="workflow_backed",
        mutates_state=True,
        accepts=("health_alert",),
        emits=("health_alert_record", "runtime_signals"),
        platform_bindings=("messaging", "feedback", "interrupt", "runtime_snapshot"),
    )
    daily_life_descriptor = AgentDescriptor(
        agent_id=dispatch_use_case.daily_life_agent.agent_id,
        display_name="Daily Life Domain Agent",
        layer="domain",
        domain="daily_life",
        status="framework_ready",
        summary="承接日常照护与生活支持记录，已接到主交互链路。",
        execution_mode="workflow_backed",
        mutates_state=True,
        accepts=("daily_life_checkin",),
        emits=("daily_life_record", "runtime_signals"),
        platform_bindings=("messaging", "feedback", "runtime_snapshot"),
    )
    mental_care_descriptor = AgentDescriptor(
        agent_id=dispatch_use_case.mental_care_agent.agent_id,
        display_name="Mental Care Domain Agent",
        layer="domain",
        domain="mental_care",
        status="framework_ready",
        summary="承接情绪关怀与心理支持记录，已接到主交互链路。",
        execution_mode="workflow_backed",
        mutates_state=True,
        accepts=("mental_care_checkin",),
        emits=("mental_care_record", "runtime_signals"),
        platform_bindings=("messaging", "feedback", "runtime_snapshot"),
    )
    profile_memory_descriptor = AgentDescriptor(
        agent_id=dispatch_use_case.profile_memory_agent.agent_id,
        display_name="Profile Memory Domain Agent",
        layer="domain",
        domain="profile_memory",
        status="framework_ready",
        summary="负责个人记忆读写，已接到主交互链路。",
        execution_mode="workflow_backed",
        mutates_state=True,
        accepts=("profile_memory_update", "profile_memory_query"),
        emits=("profile_memory_snapshot", "memory_update"),
        platform_bindings=("messaging", "memory_repository"),
    )

    registry = {
        health_descriptor.agent_id: _RegisteredAgent(
            descriptor=health_descriptor,
            run_dry_run=lambda payload: _run_health_domain_agent(dispatch_use_case.health_agent, payload),
        ),
        daily_life_descriptor.agent_id: _RegisteredAgent(
            descriptor=daily_life_descriptor,
            run_dry_run=lambda payload: _run_daily_life_domain_agent(dispatch_use_case.daily_life_agent, payload),
        ),
        mental_care_descriptor.agent_id: _RegisteredAgent(
            descriptor=mental_care_descriptor,
            run_dry_run=lambda payload: _run_mental_care_domain_agent(dispatch_use_case.mental_care_agent, payload),
        ),
        profile_memory_descriptor.agent_id: _RegisteredAgent(
            descriptor=profile_memory_descriptor,
            run_dry_run=lambda payload: _run_profile_memory_domain_agent(dispatch_use_case.profile_memory_agent, payload),
        ),
        tool_agent.agent_id: _RegisteredAgent(
            descriptor=tool_agent.describe(),
            run_dry_run=tool_agent.dry_run,
        ),
        privacy_agent.agent_id: _RegisteredAgent(
            descriptor=privacy_agent.describe(),
            run_dry_run=privacy_agent.dry_run,
        ),
        reporting_agent.agent_id: _RegisteredAgent(
            descriptor=reporting_agent.describe(),
            run_dry_run=lambda payload: reporting_agent.dry_run(
                user_id=_payload_text(payload, "user_id", "agent-preview-user"),
                source_agent=_payload_text(payload, "source_agent", "agent-registry-api"),
                trace_id=_payload_text(payload, "trace_id", "trace-agent-report-preview"),
                history_limit=_payload_int(payload, "history_limit", 3),
                memory_key=_payload_text(payload, "memory_key", ""),
            ),
        ),
    }
    return registry


def _get_registered_agent(agent_id: str, role: str) -> _RegisteredAgent:
    registry = _build_agent_registry(role)
    try:
        return registry[agent_id]
    except KeyError as exc:
        raise KeyError(agent_id) from exc


def _agent_order(registry: dict[str, _RegisteredAgent]) -> list[str]:
    preferred = [
        "health-domain-agent",
        "daily-life-domain-agent",
        "mental-care-domain-agent",
        "profile-memory-domain-agent",
        "intelligent-reporting-agent",
        "tool-agent",
        "privacy-guardian-agent",
    ]
    known = [agent_id for agent_id in preferred if agent_id in registry]
    extras = sorted(agent_id for agent_id in registry if agent_id not in preferred)
    return known + extras


def _run_health_domain_agent(agent: object, payload: dict[str, Any]) -> AgentDryRunResult:
    command = _interaction_command(payload, event_type="health_alert")
    execution_result = agent.run_interaction_cycle(command)
    result = execution_result.result
    return AgentDryRunResult(
        agent_id=agent.agent_id,
        accepted=result.flow_result.accepted,
        summary="Health domain agent executed the current health workflow.",
        execution_mode="workflow_backed",
        preview=serialize_health_workflow_result(result),
        envelope=_domain_envelope(command, agent.agent_id, "health_alert"),
        cycle=execution_result.cycle,
        notes=["This dry-run executes the real workflow and may write test data for the provided user_id."],
    )


def _run_daily_life_domain_agent(agent: object, payload: dict[str, Any]) -> AgentDryRunResult:
    command = _interaction_command(payload, event_type="daily_life_checkin")
    execution_result = agent.run_interaction_cycle(command)
    result = execution_result.result
    return AgentDryRunResult(
        agent_id=agent.agent_id,
        accepted=result.flow_result.accepted,
        summary="Daily-life domain agent executed the current daily-life workflow.",
        execution_mode="workflow_backed",
        preview=serialize_daily_life_workflow_result(result),
        envelope=_domain_envelope(command, agent.agent_id, "daily_life_checkin"),
        cycle=execution_result.cycle,
        notes=["This dry-run executes the real workflow and may write test data for the provided user_id."],
    )


def _run_mental_care_domain_agent(agent: object, payload: dict[str, Any]) -> AgentDryRunResult:
    command = _interaction_command(payload, event_type="mental_care_checkin")
    execution_result = agent.run_interaction_cycle(command)
    result = execution_result.result
    return AgentDryRunResult(
        agent_id=agent.agent_id,
        accepted=result.flow_result.accepted,
        summary="Mental-care domain agent executed the current mental-care workflow.",
        execution_mode="workflow_backed",
        preview=serialize_mental_care_workflow_result(result),
        envelope=_domain_envelope(command, agent.agent_id, "mental_care_checkin"),
        cycle=execution_result.cycle,
        notes=["This dry-run executes the real workflow and may write test data for the provided user_id."],
    )


def _run_profile_memory_domain_agent(agent: object, payload: dict[str, Any]) -> AgentDryRunResult:
    operation = _payload_text(payload, "operation", "update").lower()
    if operation == "query":
        command = _interaction_command(payload, event_type="profile_memory_query")
        execution_result = agent.run_query_cycle(command)
        result = execution_result.result
        return AgentDryRunResult(
            agent_id=agent.agent_id,
            accepted=result.query_result.accepted,
            summary="Profile-memory domain agent loaded a memory snapshot.",
            execution_mode="workflow_backed",
            preview=serialize_profile_memory_query_result(result),
            envelope=_domain_envelope(command, agent.agent_id, "profile_memory_query"),
            cycle=execution_result.cycle,
            notes=["This dry-run reads from the current profile-memory repository."],
        )

    command = _interaction_command(payload, event_type="profile_memory_update")
    execution_result = agent.run_update_cycle(command)
    result = execution_result.result
    return AgentDryRunResult(
        agent_id=agent.agent_id,
        accepted=result.flow_result.accepted,
        summary="Profile-memory domain agent executed the current memory update workflow.",
        execution_mode="workflow_backed",
        preview=serialize_profile_memory_workflow_result(result),
        envelope=_domain_envelope(command, agent.agent_id, "profile_memory_update"),
        cycle=execution_result.cycle,
        notes=["This dry-run executes the real workflow and may write test data for the provided user_id."],
    )


def _interaction_command(payload: dict[str, Any], *, event_type: str) -> UserInteractionCommand:
    return UserInteractionCommand(
        user_id=_payload_text(payload, "user_id", "agent-preview-user"),
        channel=_payload_text(payload, "channel", "agent-registry"),
        message=_payload_text(payload, "message", event_type),
        event_type=event_type,
        context=_payload_context(payload),
        trace_id=_payload_text(payload, "trace_id", f"trace-{event_type}-dry-run"),
        source_agent=_payload_text(payload, "source_agent", "agent-registry-api"),
    )


def _domain_envelope(command: UserInteractionCommand, agent_id: str, event_type: str) -> MessageEnvelope:
    return MessageEnvelope(
        from_agent=command.resolved_source_agent(),
        to_agent=agent_id,
        payload={
            "event_type": event_type,
            "user_id": command.user_id,
            "channel": command.channel,
            "context": command.context_mapping(),
        },
        trace_id=command.resolved_trace_id(),
        msg_type="DOMAIN_DISPATCH",
        require_ack=True,
    )


def _serialize_message_envelope(envelope: MessageEnvelope) -> dict[str, object]:
    payload = asdict(envelope)
    payload["priority"] = envelope.priority.value
    payload["timestamp"] = envelope.timestamp.isoformat()
    payload["expire_at"] = None if envelope.expire_at is None else envelope.expire_at.isoformat()
    return payload


def _payload_text(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _payload_int(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key)
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _payload_context(payload: dict[str, Any]) -> dict[str, Any]:
    context = payload.get("context")
    if isinstance(context, dict):
        return {str(key): value for key, value in context.items()}

    fallback: dict[str, Any] = {}
    for key in (
        "risk_level",
        "need",
        "urgency",
        "mood_signal",
        "support_need",
        "memory_key",
        "memory_value",
    ):
        if key in payload:
            fallback[key] = payload[key]
    return fallback
