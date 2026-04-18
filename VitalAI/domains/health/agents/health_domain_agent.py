"""Health domain agent wrapper for user-interaction dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from VitalAI.application.commands import HealthAlertCommand, UserInteractionCommand
from VitalAI.domains.health.models import HealthAlertSnapshot
from VitalAI.platform.agents import (
    AgentCycleTrace,
    AgentDecision,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)

if TYPE_CHECKING:
    from VitalAI.application.workflows.health_alert_workflow import HealthAlertWorkflow


@dataclass(slots=True)
class HealthDomainAgent:
    """Health-domain agent that perceives risk, decides a plan, then executes the workflow."""

    workflow: HealthAlertWorkflow
    agent_id: str = "health-domain-agent"

    def handle_interaction(self, command: UserInteractionCommand) -> object:
        """Run one health-alert interaction through the health workflow."""
        return self.run_interaction_cycle(command).result

    def run_interaction_cycle(self, command: UserInteractionCommand) -> AgentExecutionResult:
        """Run one health-alert interaction as a minimal perceive-decide-execute cycle."""
        history_snapshot = self._history_snapshot(command.user_id)
        provided_risk_level = _context_str(command, "risk_level", "")
        risk_level = _resolved_risk_level(command.message, provided_risk_level)
        signal_tags = _signal_tags(command.message, risk_level)
        open_alert_count = sum(1 for entry in history_snapshot.entries if entry.status != "resolved")
        followup_priority = _followup_priority(risk_level, open_alert_count=open_alert_count)
        next_step = _next_step(risk_level)
        perception = AgentPerception(
            summary="Health agent captured one health-risk signal and checked recent unresolved alerts.",
            signals={
                "user_id": command.user_id,
                "channel": command.channel,
                "message": command.message,
                "provided_risk_level": provided_risk_level or None,
                "risk_level": risk_level,
                "signal_tags": list(signal_tags),
                "recent_alert_count": history_snapshot.alert_count,
                "open_alert_count": open_alert_count,
                "recent_risk_levels": list(history_snapshot.recent_risk_levels[:3]),
            },
        )
        decision = AgentDecision(
            decision_type="raise_health_alert",
            summary=f"Health agent assessed {risk_level} risk and planned {followup_priority}.",
            rationale=_decision_rationale(
                risk_level=risk_level,
                signal_tags=signal_tags,
                open_alert_count=open_alert_count,
            ),
            payload={
                "risk_assessment": {
                    "level": risk_level,
                    "signal_tags": list(signal_tags),
                    "open_alert_count": open_alert_count,
                    "history_considered": history_snapshot.alert_count > 0,
                },
                "action_plan": {
                    "create_alert_record": True,
                    "followup_priority": followup_priority,
                    "next_step": next_step,
                    "workflow_input_risk_level": risk_level,
                },
            },
        )
        workflow_result = self.workflow.run(
            HealthAlertCommand(
                source_agent=self.agent_id,
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                risk_level=risk_level,
            )
        )
        execution = AgentExecution(
            action="execute_health_alert_workflow",
            status="accepted" if workflow_result.flow_result.accepted else "rejected",
            summary="Health workflow executed for the routed interaction.",
            payload=_execution_payload(workflow_result),
        )
        return AgentExecutionResult(
            result=workflow_result,
            cycle=AgentCycleTrace(
                agent_id=self.agent_id,
                perception=perception,
                decision=decision,
                execution=execution,
            ),
        )

    def _history_snapshot(self, user_id: str) -> HealthAlertSnapshot:
        """Load a small read-only view of existing alerts before deciding a new action."""
        return self.workflow.use_case.triage_service.recall_history(user_id=user_id, limit=3)


def _context_str(command: UserInteractionCommand, key: str, default: str) -> str:
    value = command.context_mapping().get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _resolved_risk_level(message: str, provided_risk_level: str) -> str:
    normalized = _normalized_risk_level(provided_risk_level)
    if normalized is not None:
        return normalized
    return _infer_risk_level(message)


def _normalized_risk_level(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in {"critical", "high", "medium", "low"}:
        return normalized
    return None


def _infer_risk_level(message: str) -> str:
    message_text = message.lower()
    if _contains_any(message_text, _CRITICAL_KEYWORDS):
        return "critical"
    if _contains_any(message_text, _HIGH_KEYWORDS):
        return "high"
    if _contains_any(message_text, _MEDIUM_KEYWORDS):
        return "medium"
    return "unknown"


def _signal_tags(message: str, risk_level: str) -> list[str]:
    message_text = message.lower()
    tags: list[str] = []
    if _contains_any(message_text, _FALL_KEYWORDS):
        tags.append("fall_signal")
    if _contains_any(message_text, _DIZZINESS_KEYWORDS):
        tags.append("dizziness_signal")
    if _contains_any(message_text, _PAIN_KEYWORDS):
        tags.append("pain_signal")
    if _contains_any(message_text, _BREATHING_KEYWORDS):
        tags.append("breathing_signal")
    if not tags:
        tags.append("general_health_signal")
    tags.append(f"risk_{risk_level}")
    return tags


def _decision_rationale(*, risk_level: str, signal_tags: list[str], open_alert_count: int) -> str:
    reasons = [f"signals={', '.join(signal_tags)}"]
    if open_alert_count > 0:
        reasons.append(f"existing_open_alerts={open_alert_count}")
    if risk_level in {"critical", "high"}:
        reasons.append("faster_followup_needed")
    return "; ".join(reasons)


def _followup_priority(risk_level: str, *, open_alert_count: int) -> str:
    if risk_level == "critical":
        return "immediate_review"
    if risk_level == "high":
        return "urgent_review" if open_alert_count == 0 else "escalated_review"
    if risk_level == "medium":
        return "priority_review"
    return "manual_review"


def _next_step(risk_level: str) -> str:
    if risk_level == "critical":
        return "urgent_health_escalation"
    if risk_level == "high":
        return "same_day_health_followup"
    if risk_level == "medium":
        return "guided_health_checkin"
    return "manual_triage"


def _execution_payload(workflow_result: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "accepted": workflow_result.flow_result.accepted,
        "runtime_signal_count": len(workflow_result.runtime_signals),
    }
    outcome = workflow_result.flow_result.outcome
    if outcome is None or outcome.history_entry is None:
        return payload
    payload.update(
        {
            "alert_id": outcome.history_entry.alert_id,
            "status": outcome.history_entry.status,
            "stored_risk_level": outcome.history_entry.risk_level,
        }
    )
    return payload


def _contains_any(message: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in message for keyword in keywords)


_CRITICAL_KEYWORDS = (
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "unconscious",
    "seizure",
    "severe bleeding",
    "胸痛",
    "呼吸困难",
    "昏迷",
    "抽搐",
    "大出血",
)
_HIGH_KEYWORDS = (
    "fall",
    "fell",
    "dizzy",
    "faint",
    "weak",
    "headache",
    "摔",
    "跌倒",
    "头晕",
    "头痛",
    "发慌",
    "胸闷",
)
_MEDIUM_KEYWORDS = (
    "fever",
    "cough",
    "nausea",
    "pain",
    "sick",
    "发烧",
    "咳嗽",
    "恶心",
    "不舒服",
    "疼",
    "痛",
)
_FALL_KEYWORDS = ("fall", "fell", "slip", "摔", "跌倒")
_DIZZINESS_KEYWORDS = ("dizzy", "faint", "lightheaded", "头晕", "眩晕")
_PAIN_KEYWORDS = ("pain", "ache", "chest pain", "疼", "痛", "胸痛", "头痛")
_BREATHING_KEYWORDS = ("can't breathe", "cannot breathe", "shortness of breath", "呼吸困难", "喘不过气")
