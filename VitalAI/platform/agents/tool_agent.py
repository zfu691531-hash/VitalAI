"""Tool agent that can execute safe internal tools and preview unsupported tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from VitalAI.application.queries import UserOverviewQuery
from VitalAI.platform.agents.agent_contract import (
    AgentCycleTrace,
    AgentDecision,
    AgentDescriptor,
    AgentDryRunResult,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority

if TYPE_CHECKING:
    from VitalAI.application.workflows.user_overview_query_workflow import UserOverviewQueryWorkflow


@dataclass(slots=True)
class ToolExecutionOutput:
    """Typed result for one tool-agent execution turn."""

    tool_name: str
    params: dict[str, Any]
    preview: dict[str, Any]
    envelope: MessageEnvelope
    execution_mode: str
    result: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolAgent:
    """Central tool gateway for safe internal tools and preview-only external requests."""

    user_overview_workflow: UserOverviewQueryWorkflow | None = None
    agent_id: str = "tool-agent"

    def describe(self) -> AgentDescriptor:
        """Return a stable registry descriptor for the tool agent."""
        return AgentDescriptor(
            agent_id=self.agent_id,
            display_name="Tool Agent",
            layer="platform",
            domain="tooling",
            status="framework_ready",
            summary="统一承接工具请求；当前已支持只读内部工具 user_overview_lookup，其余工具保持 preview-only 回退。",
            execution_mode="hybrid_tool_gateway",
            accepts=("tool_request", "tool_preview", "user_overview_lookup"),
            emits=("tool_result", "tool_preview", "tool_fallback_plan"),
            platform_bindings=("messaging", "degradation", "cache_ready", "user_overview"),
        )

    def dry_run(self, payload: dict[str, Any]) -> AgentDryRunResult:
        """Run one tool request in dry-run mode with safe internal execution when supported."""
        source_agent = _payload_text(payload, "source_agent", "agent-registry-api")
        tool_name = _payload_text(payload, "tool_name", "user_overview_lookup")
        params = _payload_mapping(payload.get("params"))
        if not params and _payload_text(payload, "user_id", ""):
            params["user_id"] = _payload_text(payload, "user_id", "")
        execution_result = self.run_tool_cycle(
            source_agent=source_agent,
            tool_name=tool_name,
            params=params,
            trace_id=_payload_text(payload, "trace_id", f"trace-tool-{tool_name}-dry-run"),
            dry_run=True,
        )
        tool_output = execution_result.result
        return AgentDryRunResult(
            agent_id=self.agent_id,
            accepted=True,
            summary=f"Tool agent handled one {tool_output.execution_mode} request for {tool_output.tool_name}.",
            execution_mode=tool_output.execution_mode,
            preview=tool_output.preview,
            envelope=tool_output.envelope,
            cycle=execution_result.cycle,
            notes=[
                "Supported internal tools execute in read-only mode during dry-run.",
                "Unsupported tools still fall back to preview-only planning.",
            ],
        )

    def run_tool_cycle(
        self,
        *,
        source_agent: str,
        tool_name: str,
        params: dict[str, Any],
        trace_id: str,
        dry_run: bool = False,
    ) -> AgentExecutionResult:
        """Run one tool request as a minimal perceive-decide-execute cycle."""
        normalized_tool_name = tool_name.strip().lower().replace("-", "_")
        normalized_params = dict(params)
        if normalized_tool_name == "user_overview_lookup" and self.user_overview_workflow is not None:
            return self._run_user_overview_lookup(
                source_agent=source_agent,
                params=normalized_params,
                trace_id=trace_id,
                dry_run=dry_run,
            )
        return self._run_preview_fallback(
            source_agent=source_agent,
            tool_name=normalized_tool_name,
            params=normalized_params,
            trace_id=trace_id,
            dry_run=dry_run,
        )

    def _run_user_overview_lookup(
        self,
        *,
        source_agent: str,
        params: dict[str, Any],
        trace_id: str,
        dry_run: bool,
    ) -> AgentExecutionResult:
        user_id = _tool_param_text(params, "user_id", "agent-preview-user")
        history_limit = _tool_param_int(params, "history_limit", 3)
        memory_key = _tool_param_text(params, "memory_key", "")
        workflow_result = self.user_overview_workflow.run(
            UserOverviewQuery(
                source_agent=self.agent_id,
                trace_id=trace_id,
                user_id=user_id,
                history_limit=history_limit,
                memory_key=memory_key,
            )
        )
        query_result = workflow_result.query_result
        perception = AgentPerception(
            summary="Tool agent classified the request as a supported internal read-only tool.",
            signals={
                "source_agent": source_agent,
                "tool_name": "user_overview_lookup",
                "user_id": user_id,
                "history_limit": history_limit,
            },
        )
        decision = AgentDecision(
            decision_type="execute_internal_tool",
            summary="Execute the user_overview_lookup internal tool.",
            rationale="The requested tool maps to an existing read-only workflow, so it can execute safely without external side effects.",
            payload={
                "tool_name": "user_overview_lookup",
                "tool_kind": "internal_read_only",
                "user_id": user_id,
                "history_limit": history_limit,
            },
        )
        envelope = MessageEnvelope(
            from_agent=source_agent,
            to_agent=self.agent_id,
            payload={
                "tool_name": "user_overview_lookup",
                "params": {
                    "user_id": user_id,
                    "history_limit": history_limit,
                    "memory_key": memory_key,
                },
                "dry_run": dry_run,
            },
            msg_type="TOOL_REQUEST",
            priority=MessagePriority.NORMAL,
            require_ack=True,
            trace_id=trace_id,
        )
        execution = AgentExecution(
            action="execute_user_overview_lookup",
            status="accepted" if query_result.accepted else "rejected",
            summary="Tool agent executed the internal user overview lookup.",
            payload={
                "accepted": query_result.accepted,
                "user_id": user_id,
                "attention_count": len(query_result.attention_items),
                "recent_activity_count": len(query_result.recent_activity),
            },
        )
        preview = {
            "tool_name": "user_overview_lookup",
            "tool_kind": "internal_read_only",
            "executed": True,
            "external_call_executed": False,
            "result": _serialize_user_overview_result(query_result),
        }
        return AgentExecutionResult(
            result=ToolExecutionOutput(
                tool_name="user_overview_lookup",
                params={
                    "user_id": user_id,
                    "history_limit": history_limit,
                    "memory_key": memory_key,
                },
                preview=preview,
                envelope=envelope,
                execution_mode="internal_tool_call",
                result=dict(preview["result"]),
            ),
            cycle=AgentCycleTrace(
                agent_id=self.agent_id,
                perception=perception,
                decision=decision,
                execution=execution,
            ),
        )

    def _run_preview_fallback(
        self,
        *,
        source_agent: str,
        tool_name: str,
        params: dict[str, Any],
        trace_id: str,
        dry_run: bool,
    ) -> AgentExecutionResult:
        perception = AgentPerception(
            summary="Tool agent parsed one tool request and normalized its parameters.",
            signals={
                "source_agent": source_agent,
                "tool_name": tool_name,
                "params": dict(params),
            },
        )
        decision = AgentDecision(
            decision_type="prepare_tool_preview",
            summary=f"Prepare one simulated tool call preview for {tool_name}.",
            rationale="This tool is not wired to a safe internal executor yet, so the agent should expose the intended call path without side effects.",
            payload={
                "tool_name": tool_name,
                "fallback_mode": "preview_only",
            },
        )
        envelope = MessageEnvelope(
            from_agent=source_agent,
            to_agent=self.agent_id,
            payload={"tool_name": tool_name, "params": dict(params), "dry_run": dry_run},
            msg_type="TOOL_REQUEST",
            priority=MessagePriority.NORMAL,
            require_ack=True,
            trace_id=trace_id,
        )
        execution = AgentExecution(
            action="emit_tool_request_preview",
            status="preview_only",
            summary="Tool agent emitted one preview-only tool request envelope.",
            payload={
                "external_call_executed": False,
                "tool_name": tool_name,
            },
        )
        return AgentExecutionResult(
            result=ToolExecutionOutput(
                tool_name=tool_name,
                params=dict(params),
                preview={
                    "tool_name": tool_name,
                    "params": dict(params),
                    "external_call_executed": False,
                    "executed": False,
                    "fallback_mode": "preview_only",
                    "platform_path": ["caller", "tool-agent", "tool-provider"],
                },
                envelope=envelope,
                execution_mode="simulated_tool_call",
                result={},
            ),
            cycle=AgentCycleTrace(
                agent_id=self.agent_id,
                perception=perception,
                decision=decision,
                execution=execution,
            ),
        )


def _payload_text(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _payload_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _tool_param_text(params: dict[str, Any], key: str, default: str) -> str:
    value = params.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _tool_param_int(params: dict[str, Any], key: str, default: int) -> int:
    value = params.get(key)
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _serialize_user_overview_result(query_result: object) -> dict[str, Any]:
    """Serialize the read-only overview so agent collaborators can reuse one stable payload."""
    profile_memory_snapshot = getattr(query_result, "profile_memory_snapshot")
    health_alert_snapshot = getattr(query_result, "health_alert_snapshot")
    daily_life_snapshot = getattr(query_result, "daily_life_snapshot")
    mental_care_snapshot = getattr(query_result, "mental_care_snapshot")
    recent_activity = getattr(query_result, "recent_activity")
    attention_items = getattr(query_result, "attention_items")
    return {
        "accepted": getattr(query_result, "accepted"),
        "user_id": getattr(query_result, "user_id"),
        "history_limit": getattr(query_result, "history_limit"),
        "latest_activity_at": getattr(query_result, "latest_activity_at"),
        "recent_activity": [asdict(item) for item in recent_activity],
        "recent_activity_count": len(recent_activity),
        "attention_summary": getattr(query_result, "attention_summary"),
        "attention_items": [asdict(item) for item in attention_items],
        "attention_count": len(attention_items),
        "overview": {
            "profile_memory": {
                "user_id": profile_memory_snapshot.user_id,
                "memory_count": profile_memory_snapshot.memory_count,
                "memory_keys": list(profile_memory_snapshot.memory_keys),
                "readable_summary": profile_memory_snapshot.readable_summary,
                "entries": [asdict(entry) for entry in profile_memory_snapshot.entries],
            },
            "health": {
                "user_id": health_alert_snapshot.user_id,
                "alert_count": health_alert_snapshot.alert_count,
                "recent_risk_levels": list(health_alert_snapshot.recent_risk_levels),
                "recent_statuses": list(health_alert_snapshot.recent_statuses),
                "readable_summary": health_alert_snapshot.readable_summary,
                "entries": [asdict(entry) for entry in health_alert_snapshot.entries],
            },
            "daily_life": {
                "user_id": daily_life_snapshot.user_id,
                "checkin_count": daily_life_snapshot.checkin_count,
                "recent_needs": list(daily_life_snapshot.recent_needs),
                "readable_summary": daily_life_snapshot.readable_summary,
                "entries": [asdict(entry) for entry in daily_life_snapshot.entries],
            },
            "mental_care": {
                "user_id": mental_care_snapshot.user_id,
                "checkin_count": mental_care_snapshot.checkin_count,
                "recent_mood_signals": list(mental_care_snapshot.recent_mood_signals),
                "recent_support_needs": list(mental_care_snapshot.recent_support_needs),
                "readable_summary": mental_care_snapshot.readable_summary,
                "entries": [asdict(entry) for entry in mental_care_snapshot.entries],
            },
        },
    }
