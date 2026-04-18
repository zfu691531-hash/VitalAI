"""Platform-level agent scaffolds exposed through the API registry."""

from VitalAI.platform.agents.agent_contract import (
    AgentCycleTrace,
    AgentDecision,
    AgentDescriptor,
    AgentDryRunResult,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)
from VitalAI.platform.agents.privacy_guardian_agent import PrivacyGuardianAgent
from VitalAI.platform.agents.tool_agent import ToolAgent

__all__ = [
    "AgentDescriptor",
    "AgentDryRunResult",
    "AgentPerception",
    "AgentDecision",
    "AgentExecution",
    "AgentCycleTrace",
    "AgentExecutionResult",
    "PrivacyGuardianAgent",
    "ToolAgent",
]
