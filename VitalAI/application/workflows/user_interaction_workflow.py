"""Backend-only user interaction workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

from VitalAI.application.commands import UserInteractionCommand, UserInteractionEventType
from VitalAI.application.commands.user_interaction_command import (
    missing_context_fields,
    supported_user_interaction_event_types,
)
from VitalAI.application.use_cases.domain_agent_dispatch import AgentHandoff, RunDomainAgentDispatchUseCase
from VitalAI.application.use_cases import (
    RunIntentDecompositionUseCase,
    RunIntentDecompositionRoutingGuardUseCase,
    RunUserInputPreprocessingUseCase,
    RunUserIntentRecognitionUseCase,
    RuntimeSignalView,
    explicit_event_type_intent_result,
    input_preprocessing_payload,
    intent_decomposition_payload,
    intent_decomposition_routing_guard_payload,
    intent_result_payload,
)

INTENT_RECOGNITION_AGENT_ID = "intent-recognition-agent"
INTENT_DECOMPOSITION_AGENT_ID = "intent-decomposition-agent"


@dataclass(slots=True)
class UserInteractionWorkflowResult:
    """Unified result for one minimal user interaction."""

    accepted: bool
    event_type: str
    routed_event_type: str | None
    user_id: str
    channel: str
    response: str
    actions: list[dict[str, object]] = field(default_factory=list)
    runtime_signals: list[RuntimeSignalView] = field(default_factory=list)
    memory_updates: dict[str, object] = field(default_factory=dict)
    agent_handoffs: list[dict[str, object]] = field(default_factory=list)
    agent_cycles: list[dict[str, object]] = field(default_factory=list)
    session: dict[str, object] = field(default_factory=dict)
    preprocessing: dict[str, object] = field(default_factory=dict)
    intent: dict[str, object] = field(default_factory=dict)
    routed_result: Any | None = None
    error: str | None = None
    error_details: dict[str, object] = field(default_factory=dict)


@dataclass
class UserInteractionWorkflow:
    """Route a minimal user interaction into existing typed workflows."""

    domain_agent_dispatch_use_case: RunDomainAgentDispatchUseCase
    intent_recognition_use_case: RunUserIntentRecognitionUseCase = field(
        default_factory=RunUserIntentRecognitionUseCase
    )
    input_preprocessing_use_case: RunUserInputPreprocessingUseCase = field(
        default_factory=RunUserInputPreprocessingUseCase
    )
    intent_decomposition_use_case: RunIntentDecompositionUseCase = field(
        default_factory=RunIntentDecompositionUseCase
    )
    intent_decomposition_routing_guard_use_case: RunIntentDecompositionRoutingGuardUseCase = field(
        default_factory=RunIntentDecompositionRoutingGuardUseCase
    )

    def run(self, command: UserInteractionCommand) -> UserInteractionWorkflowResult:
        """Execute one user interaction through the current backend-only router."""
        preprocessing = self.input_preprocessing_use_case.run(command)
        preprocessing_payload = input_preprocessing_payload(preprocessing)
        command = replace(command, message=preprocessing.normalized_message)
        validation_issues = command.validation_issues()
        if validation_issues:
            return _rejected_interaction_result(
                command=command,
                response="Invalid user interaction request",
                error="invalid_request",
                error_details={"issues": validation_issues},
                agent_handoffs=_ingress_handoffs(command),
                preprocessing=preprocessing_payload,
            )

        if command.event_type.strip():
            interaction_type = command.resolved_event_type()
            if interaction_type is None:
                return _rejected_interaction_result(
                    command=command,
                    response=f"Unsupported interaction event_type: {command.event_type}",
                    error="unsupported_event_type",
                    error_details={
                        "supported_event_types": supported_user_interaction_event_types(),
                    },
                    agent_handoffs=_ingress_handoffs(command),
                    preprocessing=preprocessing_payload,
                )
            intent_result = explicit_event_type_intent_result(interaction_type)
        else:
            intent_result = self.intent_recognition_use_case.run(command)
            if intent_result.requires_decomposition:
                intent = intent_result_payload(intent_result)
                decomposition = self.intent_decomposition_use_case.run(command, intent_result)
                decomposition_guard = self.intent_decomposition_routing_guard_use_case.run(decomposition)
                return _rejected_interaction_result(
                    command=command,
                    response=_decomposition_response(intent_result, decomposition_guard),
                    error="decomposition_needed",
                    error_details={
                        "intent": intent,
                        "decomposition": intent_decomposition_payload(decomposition),
                        "decomposition_guard": intent_decomposition_routing_guard_payload(decomposition_guard),
                    },
                    agent_handoffs=_decomposition_handoffs(
                        command,
                        decomposition_guard.status,
                    ),
                    intent=intent,
                    preprocessing=preprocessing_payload,
                )
            if intent_result.primary_intent is None or intent_result.requires_clarification:
                return _rejected_interaction_result(
                    command=command,
                    response=intent_result.clarification_prompt or "Clarification needed before routing interaction",
                    error="clarification_needed",
                    error_details={"intent": intent_result_payload(intent_result)},
                    agent_handoffs=_clarification_handoffs(command),
                    intent=intent_result_payload(intent_result),
                    preprocessing=preprocessing_payload,
                )
            interaction_type = intent_result.primary_intent
            command = _command_with_context_updates(command, intent_result.context_updates)

        missing_fields = missing_context_fields(command.context_mapping(), interaction_type)
        intent = intent_result_payload(intent_result)
        if missing_fields:
            return _rejected_interaction_result(
                command=command,
                event_type=interaction_type.value,
                response="Invalid interaction context",
                error="invalid_context",
                error_details={
                    "missing_fields": missing_fields,
                    "event_type": interaction_type.value,
                },
                agent_handoffs=_ingress_handoffs(command),
                intent=intent,
                preprocessing=preprocessing_payload,
            )
        dispatch_result = self.domain_agent_dispatch_use_case.run(command, interaction_type)
        return UserInteractionWorkflowResult(
            accepted=dispatch_result.accepted,
            event_type=dispatch_result.event_type,
            routed_event_type=dispatch_result.routed_event_type,
            user_id=command.user_id,
            channel=command.channel,
            response=dispatch_result.response,
            actions=list(dispatch_result.actions),
            runtime_signals=list(dispatch_result.runtime_signals),
            memory_updates=dict(dispatch_result.memory_updates),
            agent_handoffs=_handoff_payloads(dispatch_result.agent_handoffs),
            agent_cycles=_cycle_payloads(dispatch_result.agent_cycles),
            session=_session_payload(command),
            preprocessing=preprocessing_payload,
            intent=intent,
            routed_result=dispatch_result.routed_result,
        )
        return _rejected_interaction_result(
            command=command,
            response=f"Unsupported interaction event_type: {command.event_type}",
            error="unsupported_event_type",
            agent_handoffs=_ingress_handoffs(command),
            intent=intent,
            preprocessing=preprocessing_payload,
        )


def _decomposition_response(
    intent_result: Any,
    decomposition_guard: Any,
) -> str:
    """Return the user-facing response for a guarded decomposition result."""
    if (
        decomposition_guard.status == "clarification_candidate"
        and decomposition_guard.clarification_question
    ):
        return str(decomposition_guard.clarification_question)
    if decomposition_guard.status == "routing_candidate":
        return "Interaction decomposed into a guarded routing candidate; execution is held for review."
    if decomposition_guard.status == "hold_for_human_review":
        return "Interaction needs review before routing because the decomposition guard found risk."
    return (
        intent_result.decomposition_prompt
        or "This interaction needs second-layer intent decomposition before routing."
    )


def _rejected_interaction_result(
    *,
    command: UserInteractionCommand,
    response: str,
    error: str,
    event_type: str | None = None,
    error_details: dict[str, object] | None = None,
    agent_handoffs: list[dict[str, object]] | None = None,
    intent: dict[str, object] | None = None,
    preprocessing: dict[str, object] | None = None,
) -> UserInteractionWorkflowResult:
    """Build a stable rejected interaction response."""
    return UserInteractionWorkflowResult(
        accepted=False,
        event_type=command.event_type if event_type is None else event_type,
        routed_event_type=None,
        user_id=command.user_id,
        channel=command.channel,
        response=response,
        agent_handoffs=[] if agent_handoffs is None else list(agent_handoffs),
        session=_session_payload(command),
        preprocessing={} if preprocessing is None else preprocessing,
        intent={} if intent is None else intent,
        error=error,
        error_details={} if error_details is None else error_details,
    )


def _command_with_context_updates(
    command: UserInteractionCommand,
    context_updates: dict[str, object],
) -> UserInteractionCommand:
    """Return a command with intent-derived context updates applied."""
    if not context_updates:
        return command
    context = dict(command.context_mapping())
    for key, value in context_updates.items():
        context.setdefault(key, value)
    return replace(command, context=context)


def _session_payload(command: UserInteractionCommand) -> dict[str, object]:
    """Serialize the minimal interaction session context."""
    session = command.resolved_session_context()
    return asdict(session)


def _ingress_handoffs(command: UserInteractionCommand) -> list[dict[str, object]]:
    return _handoff_payloads(
        [
            AgentHandoff(
                agent_id=command.resolved_source_agent(),
                role="ingress_agent",
                status="received",
                notes="User interaction reached backend ingress.",
            )
        ]
    )


def _clarification_handoffs(command: UserInteractionCommand) -> list[dict[str, object]]:
    return _handoff_payloads(
        [
            AgentHandoff(
                agent_id=command.resolved_source_agent(),
                role="ingress_agent",
                status="received",
                notes="User interaction reached backend ingress.",
            ),
            AgentHandoff(
                agent_id=INTENT_RECOGNITION_AGENT_ID,
                role="intent_recognition_agent",
                status="clarification_requested",
                notes="First-layer intent recognition could not safely route the request.",
            ),
        ]
    )


def _decomposition_handoffs(
    command: UserInteractionCommand,
    decomposition_status: str,
) -> list[dict[str, object]]:
    return _handoff_payloads(
        [
            AgentHandoff(
                agent_id=command.resolved_source_agent(),
                role="ingress_agent",
                status="received",
                notes="User interaction reached backend ingress.",
            ),
            AgentHandoff(
                agent_id=INTENT_RECOGNITION_AGENT_ID,
                role="intent_recognition_agent",
                status="requires_decomposition",
                notes="First-layer recognition detected a compound interaction.",
            ),
            AgentHandoff(
                agent_id=INTENT_DECOMPOSITION_AGENT_ID,
                role="intent_decomposition_agent",
                status=decomposition_status,
                notes="Second-layer decomposition produced a guarded, non-executing result.",
            ),
        ]
    )


def _handoff_payloads(handoffs: list[AgentHandoff]) -> list[dict[str, object]]:
    return [asdict(item) for item in handoffs]


def _cycle_payloads(cycles: list[Any]) -> list[dict[str, object]]:
    return [asdict(item) for item in cycles]
