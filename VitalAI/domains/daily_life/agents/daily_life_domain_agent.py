"""Daily-life domain agent wrapper for user-interaction dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from VitalAI.application.commands import DailyLifeCheckInCommand, UserInteractionCommand
from VitalAI.platform.agents import (
    AgentCycleTrace,
    AgentDecision,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)

if TYPE_CHECKING:
    from VitalAI.application.workflows.daily_life_checkin_workflow import DailyLifeCheckInWorkflow


@dataclass(slots=True)
class DailyLifeDomainAgent:
    """Thin daily-life agent that forwards routed interactions to the daily-life workflow."""

    workflow: DailyLifeCheckInWorkflow
    agent_id: str = "daily-life-domain-agent"

    def handle_interaction(self, command: UserInteractionCommand) -> object:
        """Run one daily-life interaction through the daily-life workflow."""
        return self.run_interaction_cycle(command).result

    def run_interaction_cycle(self, command: UserInteractionCommand) -> AgentExecutionResult:
        """Run one daily-life interaction as a minimal perceive-decide-execute cycle."""
        need = _context_str(command, "need", command.message)
        urgency = _context_str(command, "urgency", "normal")
        perception = AgentPerception(
            summary="Daily-life agent extracted one care need and urgency from the routed interaction.",
            signals={
                "user_id": command.user_id,
                "channel": command.channel,
                "message": command.message,
                "need": need,
                "urgency": urgency,
            },
        )
        decision = AgentDecision(
            decision_type="record_daily_life_checkin",
            summary=f"Record one daily-life need with {urgency} urgency.",
            rationale="Daily-life support should first become an explicit check-in record so it can be tracked and surfaced later.",
            payload={
                "need": need,
                "urgency": urgency,
                "workflow": "daily_life_checkin_workflow",
            },
        )
        workflow_result = self.workflow.run(
            DailyLifeCheckInCommand(
                source_agent=self.agent_id,
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                need=need,
                urgency=urgency,
            )
        )
        execution = AgentExecution(
            action="execute_daily_life_workflow",
            status="accepted" if workflow_result.flow_result.accepted else "rejected",
            summary="Daily-life workflow executed for the routed interaction.",
            payload={
                "accepted": workflow_result.flow_result.accepted,
                "runtime_signal_count": len(workflow_result.runtime_signals),
            },
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


def _context_str(command: UserInteractionCommand, key: str, default: str) -> str:
    value = command.context_mapping().get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text
