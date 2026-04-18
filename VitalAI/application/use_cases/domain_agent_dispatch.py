"""Explicit domain-agent dispatch for user interactions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from VitalAI.application.commands import UserInteractionCommand, UserInteractionEventType
from VitalAI.domains.daily_life.agents import DailyLifeDomainAgent
from VitalAI.domains.health.agents import HealthDomainAgent
from VitalAI.domains.mental_care.agents import MentalCareDomainAgent
from VitalAI.domains.profile_memory.agents import ProfileMemoryDomainAgent
from VitalAI.platform.agents import AgentCycleTrace


@dataclass(frozen=True, slots=True)
class AgentHandoff:
    """One lightweight record describing how an interaction moved across agents."""

    agent_id: str
    role: str
    status: str
    event_type: str | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DomainAgentDispatchResult:
    """Unified result returned after dispatching an interaction to one domain agent."""

    accepted: bool
    event_type: str
    routed_event_type: str
    response: str
    actions: list[dict[str, object]]
    runtime_signals: list[Any] = field(default_factory=list)
    memory_updates: dict[str, object] = field(default_factory=dict)
    routed_result: Any | None = None
    agent_handoffs: list[AgentHandoff] = field(default_factory=list)
    agent_cycles: list[AgentCycleTrace] = field(default_factory=list)


@dataclass(slots=True)
class RunDomainAgentDispatchUseCase:
    """Dispatch one routed interaction through an explicit domain-agent boundary."""

    health_agent: HealthDomainAgent
    daily_life_agent: DailyLifeDomainAgent
    mental_care_agent: MentalCareDomainAgent
    profile_memory_agent: ProfileMemoryDomainAgent

    def run(
        self,
        command: UserInteractionCommand,
        interaction_type: UserInteractionEventType,
    ) -> DomainAgentDispatchResult:
        """Dispatch one interaction into the matching domain agent."""
        if interaction_type is UserInteractionEventType.HEALTH_ALERT:
            execution_result = self.health_agent.run_interaction_cycle(command)
            result = execution_result.result
            return DomainAgentDispatchResult(
                accepted=result.flow_result.accepted,
                event_type="health_alert",
                routed_event_type="HEALTH_ALERT",
                response=_decision_text(result, "health_alert_processed"),
                actions=[
                    {
                        "type": "review_health_alert",
                        "priority": _health_followup_priority(execution_result.cycle),
                    }
                ],
                runtime_signals=list(result.runtime_signals),
                routed_result=result,
                agent_handoffs=_build_domain_agent_handoffs(
                    source_agent=command.resolved_source_agent(),
                    domain_agent_id=self.health_agent.agent_id,
                    event_type="health_alert",
                ),
                agent_cycles=[execution_result.cycle],
            )
        if interaction_type is UserInteractionEventType.DAILY_LIFE_CHECKIN:
            execution_result = self.daily_life_agent.run_interaction_cycle(command)
            result = execution_result.result
            return DomainAgentDispatchResult(
                accepted=result.flow_result.accepted,
                event_type="daily_life_checkin",
                routed_event_type="DAILY_LIFE_CHECKIN",
                response=_decision_text(result, "daily_life_checkin_processed"),
                actions=[{"type": "support_daily_life", "urgency": _context_str(command, "urgency", "normal")}],
                runtime_signals=list(result.runtime_signals),
                routed_result=result,
                agent_handoffs=_build_domain_agent_handoffs(
                    source_agent=command.resolved_source_agent(),
                    domain_agent_id=self.daily_life_agent.agent_id,
                    event_type="daily_life_checkin",
                ),
                agent_cycles=[execution_result.cycle],
            )
        if interaction_type is UserInteractionEventType.MENTAL_CARE_CHECKIN:
            execution_result = self.mental_care_agent.run_interaction_cycle(command)
            result = execution_result.result
            return DomainAgentDispatchResult(
                accepted=result.flow_result.accepted,
                event_type="mental_care_checkin",
                routed_event_type="MENTAL_CARE_CHECKIN",
                response=_decision_text(result, "mental_care_checkin_processed"),
                actions=[
                    {
                        "type": "offer_mental_care",
                        "support_need": _context_str(command, "support_need", "companionship"),
                    }
                ],
                runtime_signals=list(result.runtime_signals),
                routed_result=result,
                agent_handoffs=_build_domain_agent_handoffs(
                    source_agent=command.resolved_source_agent(),
                    domain_agent_id=self.mental_care_agent.agent_id,
                    event_type="mental_care_checkin",
                ),
                agent_cycles=[execution_result.cycle],
            )
        if interaction_type is UserInteractionEventType.PROFILE_MEMORY_UPDATE:
            execution_result = self.profile_memory_agent.run_update_cycle(command)
            result = execution_result.result
            memory_updates: dict[str, object] = {}
            if result.flow_result.outcome is not None:
                memory_updates = {
                    "stored_entry": asdict(result.flow_result.outcome.stored_entry),
                    "profile_snapshot": _snapshot_payload(result.flow_result.outcome.profile_snapshot),
                }
            return DomainAgentDispatchResult(
                accepted=result.flow_result.accepted,
                event_type="profile_memory_update",
                routed_event_type="PROFILE_MEMORY_UPDATE",
                response=_decision_text(result, "profile_memory_updated"),
                actions=[{"type": "memory_upserted", "memory_key": _context_str(command, "memory_key", "general_note")}],
                runtime_signals=list(result.runtime_signals),
                memory_updates=memory_updates,
                routed_result=result,
                agent_handoffs=_build_domain_agent_handoffs(
                    source_agent=command.resolved_source_agent(),
                    domain_agent_id=self.profile_memory_agent.agent_id,
                    event_type="profile_memory_update",
                ),
                agent_cycles=[execution_result.cycle],
            )
        if interaction_type is UserInteractionEventType.PROFILE_MEMORY_QUERY:
            execution_result = self.profile_memory_agent.run_query_cycle(command)
            result = execution_result.result
            snapshot = result.query_result.outcome.profile_snapshot
            return DomainAgentDispatchResult(
                accepted=result.query_result.accepted,
                event_type="profile_memory_query",
                routed_event_type="PROFILE_MEMORY_QUERY",
                response="profile_memory_snapshot_loaded",
                actions=[{"type": "memory_snapshot_loaded", "memory_count": snapshot.memory_count}],
                runtime_signals=[],
                memory_updates={"profile_snapshot": _snapshot_payload(snapshot)},
                routed_result=result,
                agent_handoffs=_build_domain_agent_handoffs(
                    source_agent=command.resolved_source_agent(),
                    domain_agent_id=self.profile_memory_agent.agent_id,
                    event_type="profile_memory_query",
                ),
                agent_cycles=[execution_result.cycle],
            )
        raise ValueError(f"Unsupported interaction type for domain-agent dispatch: {interaction_type.value}")


def _build_domain_agent_handoffs(
    *,
    source_agent: str,
    domain_agent_id: str,
    event_type: str,
) -> list[AgentHandoff]:
    """Build a stable ingress-to-domain-agent handoff trace."""
    return [
        AgentHandoff(
            agent_id=source_agent,
            role="ingress_agent",
            status="received",
            event_type=event_type,
            notes="User interaction entered the backend ingress.",
        ),
        AgentHandoff(
            agent_id=domain_agent_id,
            role="domain_agent",
            status="routed",
            event_type=event_type,
            notes="Interaction was handed off to the domain agent for workflow execution.",
        ),
    ]


def _context_str(command: UserInteractionCommand, key: str, default: str) -> str:
    value = command.context_mapping().get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _decision_text(result: Any, fallback: str) -> str:
    outcome = result.flow_result.outcome
    if outcome is None:
        return fallback
    decision = outcome.decision_message.payload.get("decision")
    return fallback if decision is None else str(decision)


def _snapshot_payload(snapshot: Any) -> dict[str, object]:
    return {
        "user_id": snapshot.user_id,
        "memory_count": snapshot.memory_count,
        "memory_keys": list(snapshot.memory_keys),
        "readable_summary": snapshot.readable_summary,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }


def _health_followup_priority(cycle: AgentCycleTrace) -> str:
    payload = cycle.decision.payload
    action_plan = payload.get("action_plan")
    if not isinstance(action_plan, dict):
        return "manual_review"
    priority = action_plan.get("followup_priority")
    if priority is None:
        return "manual_review"
    return str(priority)
