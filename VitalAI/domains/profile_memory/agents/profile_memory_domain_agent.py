"""Profile-memory domain agent wrapper for user-interaction dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from VitalAI.application.commands import ProfileMemoryUpdateCommand, UserInteractionCommand
from VitalAI.application.queries import ProfileMemorySnapshotQuery
from VitalAI.platform.agents import (
    AgentCycleTrace,
    AgentDecision,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)

if TYPE_CHECKING:
    from VitalAI.application.workflows.profile_memory_query_workflow import ProfileMemoryQueryWorkflow
    from VitalAI.application.workflows.profile_memory_workflow import ProfileMemoryWorkflow


@dataclass(slots=True)
class ProfileMemoryDomainAgent:
    """Thin profile-memory agent that forwards update/query interactions to existing workflows."""

    update_workflow: ProfileMemoryWorkflow
    query_workflow: ProfileMemoryQueryWorkflow
    agent_id: str = "profile-memory-domain-agent"

    def handle_update_interaction(self, command: UserInteractionCommand) -> object:
        """Run one profile-memory update interaction."""
        return self.run_update_cycle(command).result

    def run_update_cycle(self, command: UserInteractionCommand) -> AgentExecutionResult:
        """Run one profile-memory update as a minimal perceive-decide-execute cycle."""
        memory_key = _context_str(command, "memory_key", "general_note")
        memory_value = _context_str(command, "memory_value", command.message)
        perception = AgentPerception(
            summary="Profile-memory agent extracted one memory key/value pair from the routed interaction.",
            signals={
                "user_id": command.user_id,
                "channel": command.channel,
                "message": command.message,
                "memory_key": memory_key,
                "memory_value": memory_value,
            },
        )
        decision = AgentDecision(
            decision_type="store_profile_memory",
            summary=f"Store one memory under key {memory_key}.",
            rationale="Profile memory should preserve important user facts in a structured, queryable form.",
            payload={
                "memory_key": memory_key,
                "workflow": "profile_memory_workflow",
            },
        )
        workflow_result = self.update_workflow.run(
            ProfileMemoryUpdateCommand(
                source_agent=self.agent_id,
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                memory_key=memory_key,
                memory_value=memory_value,
            )
        )
        execution = AgentExecution(
            action="execute_profile_memory_update_workflow",
            status="accepted" if workflow_result.flow_result.accepted else "rejected",
            summary="Profile-memory update workflow executed for the routed interaction.",
            payload={
                "accepted": workflow_result.flow_result.accepted,
                "memory_key": memory_key,
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

    def handle_query_interaction(self, command: UserInteractionCommand) -> object:
        """Run one profile-memory query interaction."""
        return self.run_query_cycle(command).result

    def run_query_cycle(self, command: UserInteractionCommand) -> AgentExecutionResult:
        """Run one profile-memory query as a minimal perceive-decide-execute cycle."""
        memory_key = _context_str(command, "memory_key", "")
        perception = AgentPerception(
            summary="Profile-memory agent identified which memory scope the user wants to load.",
            signals={
                "user_id": command.user_id,
                "channel": command.channel,
                "message": command.message,
                "memory_key": memory_key,
            },
        )
        decision = AgentDecision(
            decision_type="load_profile_memory",
            summary="Load one profile-memory snapshot for the current user.",
            rationale="Read requests should surface the relevant stored memory snapshot instead of mutating state.",
            payload={
                "memory_key": memory_key,
                "workflow": "profile_memory_query_workflow",
            },
        )
        workflow_result = self.query_workflow.run(
            ProfileMemorySnapshotQuery(
                source_agent=self.agent_id,
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                memory_key=memory_key,
            )
        )
        execution = AgentExecution(
            action="execute_profile_memory_query_workflow",
            status="accepted" if workflow_result.query_result.accepted else "rejected",
            summary="Profile-memory query workflow executed for the routed interaction.",
            payload={
                "accepted": workflow_result.query_result.accepted,
                "memory_key": memory_key,
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
