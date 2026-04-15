"""Backend-only user interaction workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

from VitalAI.application.commands import (
    DailyLifeCheckInCommand,
    HealthAlertCommand,
    MentalCareCheckInCommand,
    ProfileMemoryUpdateCommand,
    UserInteractionCommand,
    UserInteractionEventType,
)
from VitalAI.application.commands.user_interaction_command import (
    missing_context_fields,
    supported_user_interaction_event_types,
)
from VitalAI.application.queries import ProfileMemorySnapshotQuery
from VitalAI.application.use_cases import (
    RunIntentDecompositionUseCase,
    RunUserIntentRecognitionUseCase,
    RuntimeSignalView,
    explicit_event_type_intent_result,
    intent_decomposition_payload,
    intent_result_payload,
)
from VitalAI.application.workflows.daily_life_checkin_workflow import DailyLifeCheckInWorkflow
from VitalAI.application.workflows.health_alert_workflow import HealthAlertWorkflow
from VitalAI.application.workflows.mental_care_checkin_workflow import MentalCareCheckInWorkflow
from VitalAI.application.workflows.profile_memory_query_workflow import ProfileMemoryQueryWorkflow
from VitalAI.application.workflows.profile_memory_workflow import ProfileMemoryWorkflow


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
    session: dict[str, object] = field(default_factory=dict)
    intent: dict[str, object] = field(default_factory=dict)
    routed_result: Any | None = None
    error: str | None = None
    error_details: dict[str, object] = field(default_factory=dict)


@dataclass
class UserInteractionWorkflow:
    """Route a minimal user interaction into existing typed workflows."""

    health_workflow: HealthAlertWorkflow
    daily_life_workflow: DailyLifeCheckInWorkflow
    mental_care_workflow: MentalCareCheckInWorkflow
    profile_memory_workflow: ProfileMemoryWorkflow
    profile_memory_query_workflow: ProfileMemoryQueryWorkflow
    intent_recognition_use_case: RunUserIntentRecognitionUseCase = field(
        default_factory=RunUserIntentRecognitionUseCase
    )
    intent_decomposition_use_case: RunIntentDecompositionUseCase = field(
        default_factory=RunIntentDecompositionUseCase
    )

    def run(self, command: UserInteractionCommand) -> UserInteractionWorkflowResult:
        """Execute one user interaction through the current backend-only router."""
        validation_issues = command.validation_issues()
        if validation_issues:
            return _rejected_interaction_result(
                command=command,
                response="Invalid user interaction request",
                error="invalid_request",
                error_details={"issues": validation_issues},
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
                )
            intent_result = explicit_event_type_intent_result(interaction_type)
        else:
            intent_result = self.intent_recognition_use_case.run(command)
            if intent_result.requires_decomposition:
                intent = intent_result_payload(intent_result)
                decomposition = self.intent_decomposition_use_case.run(command, intent_result)
                return _rejected_interaction_result(
                    command=command,
                    response=(
                        intent_result.decomposition_prompt
                        or "This interaction needs second-layer intent decomposition before routing."
                    ),
                    error="decomposition_needed",
                    error_details={
                        "intent": intent,
                        "decomposition": intent_decomposition_payload(decomposition),
                    },
                    intent=intent,
                )
            if intent_result.primary_intent is None or intent_result.requires_clarification:
                return _rejected_interaction_result(
                    command=command,
                    response=intent_result.clarification_prompt or "Clarification needed before routing interaction",
                    error="clarification_needed",
                    error_details={"intent": intent_result_payload(intent_result)},
                    intent=intent_result_payload(intent_result),
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
                intent=intent,
            )

        if interaction_type is UserInteractionEventType.HEALTH_ALERT:
            return self._run_health_alert(command, intent)
        if interaction_type is UserInteractionEventType.DAILY_LIFE_CHECKIN:
            return self._run_daily_life_checkin(command, intent)
        if interaction_type is UserInteractionEventType.MENTAL_CARE_CHECKIN:
            return self._run_mental_care_checkin(command, intent)
        if interaction_type is UserInteractionEventType.PROFILE_MEMORY_UPDATE:
            return self._run_profile_memory_update(command, intent)
        if interaction_type is UserInteractionEventType.PROFILE_MEMORY_QUERY:
            return self._run_profile_memory_query(command, intent)
        return _rejected_interaction_result(
            command=command,
            response=f"Unsupported interaction event_type: {command.event_type}",
            error="unsupported_event_type",
            intent=intent,
        )

    def _run_health_alert(
        self,
        command: UserInteractionCommand,
        intent: dict[str, object],
    ) -> UserInteractionWorkflowResult:
        result = self.health_workflow.run(
            HealthAlertCommand(
                source_agent=command.resolved_source_agent(),
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                risk_level=_context_str(command, "risk_level", command.message),
            )
        )
        return _flow_interaction_result(
            command=command,
            event_type="health_alert",
            routed_event_type="HEALTH_ALERT",
            response=_decision_text(result, "health_alert_processed"),
            actions=[{"type": "review_health_alert", "priority": _context_str(command, "risk_level", "unknown")}],
            result=result,
            intent=intent,
        )

    def _run_daily_life_checkin(
        self,
        command: UserInteractionCommand,
        intent: dict[str, object],
    ) -> UserInteractionWorkflowResult:
        result = self.daily_life_workflow.run(
            DailyLifeCheckInCommand(
                source_agent=command.resolved_source_agent(),
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                need=_context_str(command, "need", command.message),
                urgency=_context_str(command, "urgency", "normal"),
            )
        )
        return _flow_interaction_result(
            command=command,
            event_type="daily_life_checkin",
            routed_event_type="DAILY_LIFE_CHECKIN",
            response=_decision_text(result, "daily_life_checkin_processed"),
            actions=[{"type": "support_daily_life", "urgency": _context_str(command, "urgency", "normal")}],
            result=result,
            intent=intent,
        )

    def _run_mental_care_checkin(
        self,
        command: UserInteractionCommand,
        intent: dict[str, object],
    ) -> UserInteractionWorkflowResult:
        result = self.mental_care_workflow.run(
            MentalCareCheckInCommand(
                source_agent=command.resolved_source_agent(),
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                mood_signal=_context_str(command, "mood_signal", command.message),
                support_need=_context_str(command, "support_need", "companionship"),
            )
        )
        return _flow_interaction_result(
            command=command,
            event_type="mental_care_checkin",
            routed_event_type="MENTAL_CARE_CHECKIN",
            response=_decision_text(result, "mental_care_checkin_processed"),
            actions=[{"type": "offer_mental_care", "support_need": _context_str(command, "support_need", "companionship")}],
            result=result,
            intent=intent,
        )

    def _run_profile_memory_update(
        self,
        command: UserInteractionCommand,
        intent: dict[str, object],
    ) -> UserInteractionWorkflowResult:
        result = self.profile_memory_workflow.run(
            ProfileMemoryUpdateCommand(
                source_agent=command.resolved_source_agent(),
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
                memory_key=_context_str(command, "memory_key", "general_note"),
                memory_value=_context_str(command, "memory_value", command.message),
            )
        )
        memory_updates: dict[str, object] = {}
        if result.flow_result.outcome is not None:
            memory_updates = {
                "stored_entry": asdict(result.flow_result.outcome.stored_entry),
                "profile_snapshot": _snapshot_payload(result.flow_result.outcome.profile_snapshot),
            }
        return _flow_interaction_result(
            command=command,
            event_type="profile_memory_update",
            routed_event_type="PROFILE_MEMORY_UPDATE",
            response=_decision_text(result, "profile_memory_updated"),
            actions=[{"type": "memory_upserted", "memory_key": _context_str(command, "memory_key", "general_note")}],
            result=result,
            memory_updates=memory_updates,
            intent=intent,
        )

    def _run_profile_memory_query(
        self,
        command: UserInteractionCommand,
        intent: dict[str, object],
    ) -> UserInteractionWorkflowResult:
        result = self.profile_memory_query_workflow.run(
            ProfileMemorySnapshotQuery(
                source_agent=command.resolved_source_agent(),
                trace_id=command.resolved_trace_id(),
                user_id=command.user_id,
            )
        )
        snapshot = result.query_result.outcome.profile_snapshot
        return UserInteractionWorkflowResult(
            accepted=result.query_result.accepted,
            event_type="profile_memory_query",
            routed_event_type="PROFILE_MEMORY_QUERY",
            user_id=command.user_id,
            channel=command.channel,
            response="profile_memory_snapshot_loaded",
            actions=[{"type": "memory_snapshot_loaded", "memory_count": snapshot.memory_count}],
            runtime_signals=[],
            memory_updates={"profile_snapshot": _snapshot_payload(snapshot)},
            session=_session_payload(command),
            intent=intent,
            routed_result=result,
        )


def _flow_interaction_result(
    *,
    command: UserInteractionCommand,
    event_type: str,
    routed_event_type: str,
    response: str,
    actions: list[dict[str, object]],
    result: Any,
    intent: dict[str, object],
    memory_updates: dict[str, object] | None = None,
) -> UserInteractionWorkflowResult:
    """Wrap one routed typed-flow result in the interaction response shape."""
    return UserInteractionWorkflowResult(
        accepted=result.flow_result.accepted,
        event_type=event_type,
        routed_event_type=routed_event_type,
        user_id=command.user_id,
        channel=command.channel,
        response=response,
        actions=actions,
        runtime_signals=list(result.runtime_signals),
        memory_updates={} if memory_updates is None else memory_updates,
        session=_session_payload(command),
        intent=intent,
        routed_result=result,
    )


def _rejected_interaction_result(
    *,
    command: UserInteractionCommand,
    response: str,
    error: str,
    event_type: str | None = None,
    error_details: dict[str, object] | None = None,
    intent: dict[str, object] | None = None,
) -> UserInteractionWorkflowResult:
    """Build a stable rejected interaction response."""
    return UserInteractionWorkflowResult(
        accepted=False,
        event_type=command.event_type if event_type is None else event_type,
        routed_event_type=None,
        user_id=command.user_id,
        channel=command.channel,
        response=response,
        session=_session_payload(command),
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


def _decision_text(result: Any, fallback: str) -> str:
    """Extract a concise decision response from a workflow result."""
    outcome = result.flow_result.outcome
    if outcome is None:
        return fallback
    decision = outcome.decision_message.payload.get("decision")
    return fallback if decision is None else str(decision)


def _context_str(command: UserInteractionCommand, key: str, default: str) -> str:
    """Read a string value from the interaction context with a fallback."""
    value = command.context_mapping().get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _session_payload(command: UserInteractionCommand) -> dict[str, object]:
    """Serialize the minimal interaction session context."""
    session = command.resolved_session_context()
    return asdict(session)


def _snapshot_payload(snapshot: Any) -> dict[str, object]:
    """Serialize a profile-memory snapshot for the interaction contract."""
    return {
        "user_id": snapshot.user_id,
        "memory_count": snapshot.memory_count,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }
