"""Mental-care domain agent wrapper for user-interaction dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from VitalAI.application.commands import MentalCareCheckInCommand, UserInteractionCommand
from VitalAI.platform.agents import (
    AgentCycleTrace,
    AgentDecision,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)

if TYPE_CHECKING:
    from VitalAI.application.workflows.mental_care_checkin_workflow import MentalCareCheckInWorkflow


@dataclass(slots=True)
class MentalCareDomainAgent:
    """Thin mental-care agent that forwards routed interactions to the mental-care workflow."""

    workflow: MentalCareCheckInWorkflow
    agent_id: str = "mental-care-domain-agent"

    def handle_interaction(self, command: UserInteractionCommand) -> object:
        """Run one mental-care interaction through the mental-care workflow."""
        return self.run_interaction_cycle(command).result

    def run_interaction_cycle(self, command: UserInteractionCommand) -> AgentExecutionResult:
        """Run one mental-care interaction as a minimal perceive-decide-execute cycle."""
        mood_signal = _context_str(command, "mood_signal", command.message)
        support_need = _context_str(command, "support_need", "companionship")
        perception = AgentPerception(
            summary="Mental-care agent extracted mood and support signals from the routed interaction.",
            signals={
                "user_id": command.user_id,
                "channel": command.channel,
                "message": command.message,
                "mood_signal": mood_signal,
                "support_need": support_need,
            },
        )
        decision = AgentDecision(
            decision_type="record_mental_care_checkin",
            summary=f"Record one mental-care interaction for {support_need}.",
            rationale="Emotional support should first become a structured check-in so later care decisions can see the history.",
            payload={
                "mood_signal": mood_signal,
                "support_need": support_need,
                "workflow": "mental_care_checkin_workflow",
            },
        )
        workflow_result = self.workflow.run(
            MentalCareCheckInCommand(
                source_agent=self.agent_id,
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                mood_signal=mood_signal,
                support_need=support_need,
            )
        )
        execution = AgentExecution(
            action="execute_mental_care_workflow",
            status="accepted" if workflow_result.flow_result.accepted else "rejected",
            summary="Mental-care workflow executed for the routed interaction.",
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
