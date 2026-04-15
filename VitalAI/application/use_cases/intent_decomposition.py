"""Typed second-layer intent decomposition boundary.

The current implementation is intentionally a placeholder: it records the
contract and first-layer hints, but it does not call an LLM or route work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol

from VitalAI.application.commands import UserInteractionCommand, UserInteractionEventType
from VitalAI.application.use_cases.intent_recognition import UserIntentResult


@dataclass(frozen=True, slots=True)
class IntentDecompositionTask:
    """One task candidate produced or hinted during intent decomposition."""

    task_type: str
    intent: UserInteractionEventType | None = None
    priority: int = 100
    confidence: float = 0.0
    source: str = "first_layer_hint"
    reason: str = ""
    slots: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IntentDecompositionRiskFlag:
    """Risk marker carried forward for second-layer decomposition."""

    kind: str
    severity: str
    reason: str


@dataclass(frozen=True, slots=True)
class IntentDecompositionResult:
    """Stable result shape for a future LLM intent decomposer."""

    status: str
    ready_for_routing: bool
    routing_decision: str
    source: str
    primary_task: IntentDecompositionTask | None = None
    secondary_tasks: tuple[IntentDecompositionTask, ...] = ()
    candidate_tasks: tuple[IntentDecompositionTask, ...] = ()
    risk_flags: tuple[IntentDecompositionRiskFlag, ...] = ()
    clarification_question: str | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class IntentDecompositionValidationIssue:
    """One schema validation issue for future LLM decomposition output."""

    field: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class IntentDecompositionValidationResult:
    """Validation result for a raw second-layer decomposition payload."""

    valid: bool
    result: IntentDecompositionResult | None = None
    issues: tuple[IntentDecompositionValidationIssue, ...] = ()


class IntentDecomposer(Protocol):
    """Stable contract for second-layer intent decomposers."""

    def decompose(
        self,
        command: UserInteractionCommand,
        intent_result: UserIntentResult,
    ) -> IntentDecompositionValidationResult:
        """Return a validated decomposition result or validation issues."""


class IntentDecompositionBackend(Protocol):
    """Backend contract for a future LLM intent decomposition adapter."""

    def generate(
        self,
        command: UserInteractionCommand,
        intent_result: UserIntentResult,
        schema: dict[str, object],
    ) -> object:
        """Generate one raw decomposition payload from command and first-layer hints."""


@dataclass(slots=True)
class RunIntentDecompositionUseCase:
    """Run the configured second-layer decomposition boundary."""

    source: str = "placeholder_intent_decomposer"
    decomposer: IntentDecomposer | None = None

    def run(
        self,
        command: UserInteractionCommand,
        intent_result: UserIntentResult,
    ) -> IntentDecompositionResult:
        """Return a typed decomposition result without directly routing work."""
        if self.decomposer is None:
            return _placeholder_decomposition_result(
                command,
                intent_result,
                source=self.source,
            )
        validation = self.decomposer.decompose(command, intent_result)
        if validation.valid and validation.result is not None:
            return validation.result
        return _invalid_decomposition_result(command, intent_result, validation.issues)


@dataclass(slots=True)
class PlaceholderIntentDecomposer:
    """No-op decomposer that preserves first-layer hints without routing."""

    placeholder_use_case: RunIntentDecompositionUseCase = field(
        default_factory=RunIntentDecompositionUseCase
    )

    def decompose(
        self,
        command: UserInteractionCommand,
        intent_result: UserIntentResult,
    ) -> IntentDecompositionValidationResult:
        """Return the current safe placeholder result as a valid non-routable output."""
        return IntentDecompositionValidationResult(
            valid=True,
            result=self.placeholder_use_case.run(command, intent_result),
        )


@dataclass(slots=True)
class LLMIntentDecomposer:
    """Adapter shell for future LLM-based decomposition.

    The backend may be any local or remote implementation, but its raw output
    must pass the local validator before the result can be considered usable.
    """

    backend: IntentDecompositionBackend | None = None
    fallback: IntentDecomposer = field(default_factory=PlaceholderIntentDecomposer)
    timeout_seconds: float = 5.0

    def decompose(
        self,
        command: UserInteractionCommand,
        intent_result: UserIntentResult,
    ) -> IntentDecompositionValidationResult:
        """Generate and validate a second-layer decomposition payload."""
        if self.backend is None:
            return self.fallback.decompose(command, intent_result)
        started_at = monotonic()
        try:
            raw_payload = self.backend.generate(
                command,
                intent_result,
                intent_decomposition_llm_output_schema(),
            )
        except Exception:
            return self.fallback.decompose(command, intent_result)
        elapsed = monotonic() - started_at
        if elapsed > self.timeout_seconds:
            return IntentDecompositionValidationResult(
                valid=False,
                issues=(
                    IntentDecompositionValidationIssue(
                        field="$",
                        code="timeout",
                        message="LLM intent decomposition exceeded the configured timeout boundary.",
                    ),
                ),
            )
        return validate_intent_decomposition_llm_payload(raw_payload)


@dataclass(slots=True)
class RunIntentDecompositionValidationUseCase:
    """Validate future LLM decomposition output before workflow routing."""

    def run(self, payload: object) -> IntentDecompositionValidationResult:
        """Validate and parse one raw decomposition payload."""
        return validate_intent_decomposition_llm_payload(payload)


def build_intent_decomposition_use_case(
    mode: str | None = None,
) -> RunIntentDecompositionUseCase:
    """Build the configured second-layer decomposition use case."""
    normalized_mode = "placeholder" if mode is None else mode.strip().lower().replace("-", "_")
    if normalized_mode == "llm":
        return RunIntentDecompositionUseCase(
            decomposer=LLMIntentDecomposer(),
        )
    return RunIntentDecompositionUseCase()


def intent_decomposition_payload(result: IntentDecompositionResult) -> dict[str, object]:
    """Serialize an intent decomposition result for API diagnostics."""
    return {
        "status": result.status,
        "ready_for_routing": result.ready_for_routing,
        "routing_decision": result.routing_decision,
        "source": result.source,
        "primary_task": _task_payload(result.primary_task),
        "secondary_tasks": [_task_payload(task) for task in result.secondary_tasks],
        "candidate_tasks": [_task_payload(task) for task in result.candidate_tasks],
        "risk_flags": [
            {"kind": flag.kind, "severity": flag.severity, "reason": flag.reason}
            for flag in result.risk_flags
        ],
        "clarification_question": result.clarification_question,
        "notes": result.notes,
    }


def intent_decomposition_validation_payload(
    validation: IntentDecompositionValidationResult,
) -> dict[str, object]:
    """Serialize a validation result for diagnostics and tests."""
    return {
        "valid": validation.valid,
        "result": None if validation.result is None else intent_decomposition_payload(validation.result),
        "issues": [
            {"field": issue.field, "code": issue.code, "message": issue.message}
            for issue in validation.issues
        ],
    }


def intent_decomposition_llm_output_schema() -> dict[str, object]:
    """Return the stable JSON-like schema expected from a future LLM adapter."""
    return {
        "type": "object",
        "required": ["status", "ready_for_routing", "routing_decision"],
        "properties": {
            "status": {"type": "string", "enum": list(_ALLOWED_DECOMPOSITION_STATUSES)},
            "ready_for_routing": {"type": "boolean"},
            "routing_decision": {"type": "string", "enum": list(_ALLOWED_ROUTING_DECISIONS)},
            "primary_task": _task_schema(nullable=True),
            "secondary_tasks": {"type": "array", "maxItems": _MAX_TASKS, "items": _task_schema()},
            "risk_flags": {"type": "array", "maxItems": _MAX_RISK_FLAGS, "items": _risk_flag_schema()},
            "clarification_question": {"type": ["string", "null"]},
            "notes": {"type": "string"},
        },
        "routing_guards": [
            "ready_for_routing=true requires primary_task",
            "route_primary/route_sequence require primary_task",
            "ask_clarification requires clarification_question",
            "LLM output is never allowed to call workflows or write repositories directly",
        ],
    }


def validate_intent_decomposition_llm_payload(
    payload: object,
) -> IntentDecompositionValidationResult:
    """Validate a raw future-LLM payload and parse it into the typed contract."""
    issues: list[IntentDecompositionValidationIssue] = []
    if not isinstance(payload, dict):
        return IntentDecompositionValidationResult(
            valid=False,
            issues=(
                IntentDecompositionValidationIssue(
                    field="$",
                    code="must_be_object",
                    message="Intent decomposition output must be a JSON object.",
                ),
            ),
        )

    status = _read_required_string(
        payload,
        field="status",
        allowed_values=_ALLOWED_DECOMPOSITION_STATUSES,
        issues=issues,
    )
    ready_for_routing = _read_required_bool(payload, field="ready_for_routing", issues=issues)
    routing_decision = _read_required_string(
        payload,
        field="routing_decision",
        allowed_values=_ALLOWED_ROUTING_DECISIONS,
        issues=issues,
    )
    primary_task = _parse_optional_task(payload.get("primary_task"), field="primary_task", issues=issues)
    secondary_tasks = _parse_task_list(
        payload.get("secondary_tasks", []),
        field="secondary_tasks",
        issues=issues,
    )
    candidate_tasks = _parse_task_list(
        payload.get("candidate_tasks", []),
        field="candidate_tasks",
        issues=issues,
    )
    risk_flags = _parse_risk_flag_list(payload.get("risk_flags", []), issues=issues)
    clarification_question = _read_optional_string(payload, "clarification_question", issues=issues)
    notes = _read_optional_string(payload, "notes", issues=issues) or ""

    _validate_routing_guards(
        ready_for_routing=ready_for_routing,
        routing_decision=routing_decision,
        primary_task=primary_task,
        clarification_question=clarification_question,
        issues=issues,
    )

    if issues:
        return IntentDecompositionValidationResult(valid=False, issues=tuple(issues))

    return IntentDecompositionValidationResult(
        valid=True,
        result=IntentDecompositionResult(
            status=status or "decomposed",
            ready_for_routing=bool(ready_for_routing),
            routing_decision=routing_decision or "hold_for_human_review",
            source="llm_schema_validated",
            primary_task=primary_task,
            secondary_tasks=tuple(secondary_tasks),
            candidate_tasks=tuple(candidate_tasks),
            risk_flags=tuple(risk_flags),
            clarification_question=clarification_question,
            notes=notes,
        ),
    )


def _task_payload(task: IntentDecompositionTask | None) -> dict[str, object] | None:
    """Serialize one task candidate."""
    if task is None:
        return None
    return {
        "task_type": task.task_type,
        "intent": None if task.intent is None else task.intent.value,
        "priority": task.priority,
        "confidence": task.confidence,
        "source": task.source,
        "reason": task.reason,
        "slots": dict(task.slots),
    }


def _placeholder_decomposition_result(
    command: UserInteractionCommand,
    intent_result: UserIntentResult,
    *,
    source: str,
) -> IntentDecompositionResult:
    """Build the safe non-routable placeholder result."""
    candidate_tasks = tuple(
        IntentDecompositionTask(
            task_type="candidate_intent",
            intent=candidate.intent,
            priority=_priority_for_intent(candidate.intent),
            confidence=candidate.confidence,
            source="first_layer_candidate",
            reason=candidate.reason,
        )
        for candidate in intent_result.candidates
    )
    return IntentDecompositionResult(
        status="pending_second_layer",
        ready_for_routing=False,
        routing_decision="hold_for_second_layer_decomposition",
        source=source,
        candidate_tasks=candidate_tasks,
        risk_flags=tuple(_risk_flags_for(command.message, intent_result)),
        clarification_question=(
            "这句话可能同时包含多个事情，需要先拆分出主任务、次任务和风险信号后再执行。"
        ),
        notes=(
            "Current placeholder preserves first-layer hints only; "
            "future LLM output must be schema-validated before routing."
        ),
    )


def _invalid_decomposition_result(
    command: UserInteractionCommand,
    intent_result: UserIntentResult,
    issues: tuple[IntentDecompositionValidationIssue, ...],
) -> IntentDecompositionResult:
    """Build a non-routable result when second-layer output fails validation."""
    issue_summary = "; ".join(f"{issue.field}:{issue.code}" for issue in issues)
    placeholder = _placeholder_decomposition_result(
        command,
        intent_result,
        source="intent_decomposition_validation_failed",
    )
    return IntentDecompositionResult(
        status="invalid_second_layer_output",
        ready_for_routing=False,
        routing_decision="hold_for_human_review",
        source="intent_decomposition_validation_failed",
        candidate_tasks=placeholder.candidate_tasks,
        risk_flags=placeholder.risk_flags,
        clarification_question=placeholder.clarification_question,
        notes=f"Second-layer output failed validation: {issue_summary}",
    )


def _task_schema(nullable: bool = False) -> dict[str, object]:
    """Return the JSON-like schema for one decomposition task."""
    schema_type: object = ["object", "null"] if nullable else "object"
    return {
        "type": schema_type,
        "required": ["task_type", "intent", "priority", "confidence"],
        "properties": {
            "task_type": {"type": "string"},
            "intent": {
                "type": ["string", "null"],
                "enum": [event_type.value for event_type in UserInteractionEventType] + [None],
            },
            "priority": {"type": "integer", "minimum": 0, "maximum": 100},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
            "slots": {"type": "object"},
        },
    }


def _risk_flag_schema() -> dict[str, object]:
    """Return the JSON-like schema for one risk flag."""
    return {
        "type": "object",
        "required": ["kind", "severity", "reason"],
        "properties": {
            "kind": {"type": "string"},
            "severity": {"type": "string", "enum": list(_ALLOWED_RISK_SEVERITIES)},
            "reason": {"type": "string"},
        },
    }


def _parse_optional_task(
    raw_task: object,
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> IntentDecompositionTask | None:
    """Parse an optional task object."""
    if raw_task is None:
        return None
    return _parse_task(raw_task, field=field, issues=issues)


def _parse_task_list(
    raw_tasks: object,
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> list[IntentDecompositionTask]:
    """Parse a bounded list of task objects."""
    if not isinstance(raw_tasks, list):
        issues.append(_issue(field, "must_be_array", "Task collection must be an array."))
        return []
    if len(raw_tasks) > _MAX_TASKS:
        issues.append(_issue(field, "too_many_items", f"Task collection can contain at most {_MAX_TASKS} items."))
    tasks: list[IntentDecompositionTask] = []
    for index, raw_task in enumerate(raw_tasks[:_MAX_TASKS]):
        parsed = _parse_task(raw_task, field=f"{field}[{index}]", issues=issues)
        if parsed is not None:
            tasks.append(parsed)
    return tasks


def _parse_task(
    raw_task: object,
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> IntentDecompositionTask | None:
    """Parse one task object while accumulating validation issues."""
    if not isinstance(raw_task, dict):
        issues.append(_issue(field, "must_be_object", "Task must be an object."))
        return None
    task_type = _read_required_string(raw_task, field=f"{field}.task_type", issues=issues)
    intent = _parse_intent_value(raw_task.get("intent"), field=f"{field}.intent", issues=issues)
    priority = _read_int_in_range(raw_task, field=f"{field}.priority", default=100, issues=issues)
    confidence = _read_float_in_range(raw_task, field=f"{field}.confidence", default=0.0, issues=issues)
    source = _read_optional_string(raw_task, "source", issues=issues) or "llm"
    reason = _read_optional_string(raw_task, "reason", issues=issues) or ""
    slots = raw_task.get("slots", {})
    if not isinstance(slots, dict):
        issues.append(_issue(f"{field}.slots", "must_be_object", "Task slots must be an object."))
        slots = {}
    if task_type is None:
        return None
    return IntentDecompositionTask(
        task_type=task_type,
        intent=intent,
        priority=priority,
        confidence=confidence,
        source=source,
        reason=reason,
        slots=slots,
    )


def _parse_risk_flag_list(
    raw_flags: object,
    *,
    issues: list[IntentDecompositionValidationIssue],
) -> list[IntentDecompositionRiskFlag]:
    """Parse a bounded risk flag list."""
    field = "risk_flags"
    if not isinstance(raw_flags, list):
        issues.append(_issue(field, "must_be_array", "Risk flags must be an array."))
        return []
    if len(raw_flags) > _MAX_RISK_FLAGS:
        issues.append(
            _issue(field, "too_many_items", f"Risk flags can contain at most {_MAX_RISK_FLAGS} items.")
        )
    flags: list[IntentDecompositionRiskFlag] = []
    for index, raw_flag in enumerate(raw_flags[:_MAX_RISK_FLAGS]):
        parsed = _parse_risk_flag(raw_flag, field=f"{field}[{index}]", issues=issues)
        if parsed is not None:
            flags.append(parsed)
    return flags


def _parse_risk_flag(
    raw_flag: object,
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> IntentDecompositionRiskFlag | None:
    """Parse one risk flag object."""
    if not isinstance(raw_flag, dict):
        issues.append(_issue(field, "must_be_object", "Risk flag must be an object."))
        return None
    kind = _read_required_string(raw_flag, field=f"{field}.kind", issues=issues)
    severity = _read_required_string(
        raw_flag,
        field=f"{field}.severity",
        allowed_values=_ALLOWED_RISK_SEVERITIES,
        issues=issues,
    )
    reason = _read_required_string(raw_flag, field=f"{field}.reason", issues=issues)
    if kind is None or severity is None or reason is None:
        return None
    return IntentDecompositionRiskFlag(kind=kind, severity=severity, reason=reason)


def _parse_intent_value(
    value: object,
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> UserInteractionEventType | None:
    """Parse one optional intent value."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        issues.append(_issue(field, "invalid_intent", "Intent must be a supported intent string or null."))
        return None
    normalized = value.strip().lower()
    try:
        return UserInteractionEventType(normalized)
    except ValueError:
        issues.append(_issue(field, "unsupported_intent", f"Unsupported intent: {value}"))
        return None


def _read_required_string(
    payload: dict[str, object],
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
    allowed_values: tuple[str, ...] | None = None,
) -> str | None:
    """Read and validate a required string field."""
    raw_value = payload.get(field.rsplit(".", 1)[-1])
    if not isinstance(raw_value, str) or not raw_value.strip():
        issues.append(_issue(field, "required", "Field must be a non-empty string."))
        return None
    value = raw_value.strip()
    if allowed_values is not None and value not in allowed_values:
        issues.append(_issue(field, "unsupported_value", f"Unsupported value: {value}"))
        return None
    return value


def _read_optional_string(
    payload: dict[str, object],
    field: str,
    *,
    issues: list[IntentDecompositionValidationIssue],
) -> str | None:
    """Read and validate an optional string field."""
    raw_value = payload.get(field)
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        issues.append(_issue(field, "must_be_string", "Field must be a string when provided."))
        return None
    value = raw_value.strip()
    return value or None


def _read_required_bool(
    payload: dict[str, object],
    *,
    field: str,
    issues: list[IntentDecompositionValidationIssue],
) -> bool | None:
    """Read and validate a required bool field."""
    raw_value = payload.get(field)
    if not isinstance(raw_value, bool):
        issues.append(_issue(field, "must_be_boolean", "Field must be a boolean."))
        return None
    return raw_value


def _read_int_in_range(
    payload: dict[str, object],
    *,
    field: str,
    default: int,
    issues: list[IntentDecompositionValidationIssue],
) -> int:
    """Read an integer in the inclusive range 0..100."""
    key = field.rsplit(".", 1)[-1]
    raw_value = payload.get(key, default)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        issues.append(_issue(field, "must_be_integer", "Field must be an integer."))
        return default
    if raw_value < 0 or raw_value > 100:
        issues.append(_issue(field, "out_of_range", "Field must be between 0 and 100."))
        return default
    return raw_value


def _read_float_in_range(
    payload: dict[str, object],
    *,
    field: str,
    default: float,
    issues: list[IntentDecompositionValidationIssue],
) -> float:
    """Read a numeric confidence in the inclusive range 0..1."""
    key = field.rsplit(".", 1)[-1]
    raw_value = payload.get(key, default)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        issues.append(_issue(field, "must_be_number", "Field must be a number."))
        return default
    value = float(raw_value)
    if value < 0.0 or value > 1.0:
        issues.append(_issue(field, "out_of_range", "Field must be between 0.0 and 1.0."))
        return default
    return value


def _validate_routing_guards(
    *,
    ready_for_routing: bool | None,
    routing_decision: str | None,
    primary_task: IntentDecompositionTask | None,
    clarification_question: str | None,
    issues: list[IntentDecompositionValidationIssue],
) -> None:
    """Validate cross-field routing guards for LLM output."""
    if ready_for_routing is True and primary_task is None:
        issues.append(_issue("primary_task", "required_for_routing", "Routing requires a primary task."))
    if routing_decision in {"route_primary", "route_sequence"} and primary_task is None:
        issues.append(_issue("routing_decision", "primary_task_required", "Route decisions require primary_task."))
    if routing_decision == "ask_clarification" and clarification_question is None:
        issues.append(
            _issue(
                "clarification_question",
                "required_for_clarification",
                "Clarification routing requires a question.",
            )
        )
    if ready_for_routing is False and routing_decision in {"route_primary", "route_sequence"}:
        issues.append(
            _issue(
                "ready_for_routing",
                "inconsistent_routing_state",
                "Route decisions require ready_for_routing=true.",
            )
        )


def _issue(field: str, code: str, message: str) -> IntentDecompositionValidationIssue:
    """Build one validation issue."""
    return IntentDecompositionValidationIssue(field=field, code=code, message=message)


def _priority_for_intent(intent: UserInteractionEventType) -> int:
    """Return deterministic routing priority hints without making a decision."""
    if intent is UserInteractionEventType.HEALTH_ALERT:
        return 10
    if intent is UserInteractionEventType.MENTAL_CARE_CHECKIN:
        return 30
    if intent is UserInteractionEventType.PROFILE_MEMORY_UPDATE:
        return 40
    if intent is UserInteractionEventType.PROFILE_MEMORY_QUERY:
        return 45
    if intent is UserInteractionEventType.DAILY_LIFE_CHECKIN:
        return 60
    return 100


def _risk_flags_for(
    text: str,
    intent_result: UserIntentResult,
) -> list[IntentDecompositionRiskFlag]:
    """Derive lightweight risk flags from first-layer hints and surface text."""
    normalized = text.strip().lower()
    flags: list[IntentDecompositionRiskFlag] = []
    intents = {candidate.intent for candidate in intent_result.candidates}
    if UserInteractionEventType.HEALTH_ALERT in intents:
        flags.append(
            IntentDecompositionRiskFlag(
                kind="health_signal",
                severity="high",
                reason="first_layer_candidate:health_alert",
            )
        )
    if _contains_any(normalized, ("药", "吃药", "medicine", "medication")):
        flags.append(
            IntentDecompositionRiskFlag(
                kind="medication_signal",
                severity="medium",
                reason="surface_text_mentions_medication",
            )
        )
    if _contains_any(normalized, ("胸口", "煤气", "摔倒", "手脚发麻", "chest", "fall", "gas")):
        flags.append(
            IntentDecompositionRiskFlag(
                kind="safety_or_urgent_signal",
                severity="high",
                reason="surface_text_mentions_safety_or_urgent_term",
            )
        )
    return flags


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Return whether any keyword is present in text."""
    return any(keyword in text for keyword in keywords)


_ALLOWED_DECOMPOSITION_STATUSES = (
    "decomposed",
    "needs_clarification",
    "hold_for_human_review",
)

_ALLOWED_ROUTING_DECISIONS = (
    "route_primary",
    "route_sequence",
    "ask_clarification",
    "hold_for_human_review",
    "reject",
)

_ALLOWED_RISK_SEVERITIES = ("low", "medium", "high", "critical")

_MAX_TASKS = 5
_MAX_RISK_FLAGS = 8
