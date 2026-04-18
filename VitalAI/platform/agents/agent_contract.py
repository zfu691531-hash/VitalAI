"""Shared contracts for lightweight platform-connected agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from VitalAI.platform.messaging import MessageEnvelope


@dataclass(frozen=True, slots=True)
class AgentDescriptor:
    """Describe one agent that can be surfaced through the API registry."""

    agent_id: str
    display_name: str
    layer: str
    domain: str
    status: str
    summary: str
    execution_mode: str
    mutates_state: bool = False
    accepts: tuple[str, ...] = ()
    emits: tuple[str, ...] = ()
    platform_bindings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentPerception:
    """What one agent extracted from the current input and local context."""

    summary: str
    signals: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentDecision:
    """Structured decision produced after one agent reasons over perceived signals."""

    decision_type: str
    summary: str
    rationale: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentExecution:
    """Execution summary after the agent commits to one concrete action."""

    action: str
    status: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentCycleTrace:
    """Minimal perceive-decide-execute trace for one agent turn."""

    agent_id: str
    perception: AgentPerception
    decision: AgentDecision
    execution: AgentExecution


@dataclass(slots=True)
class AgentExecutionResult:
    """One agent run result paired with its cycle trace."""

    result: Any
    cycle: AgentCycleTrace


@dataclass(slots=True)
class AgentDryRunResult:
    """Serializable dry-run result returned by the agent registry API."""

    agent_id: str
    accepted: bool
    summary: str
    execution_mode: str
    preview: dict[str, Any] = field(default_factory=dict)
    envelope: MessageEnvelope | None = None
    cycle: AgentCycleTrace | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
