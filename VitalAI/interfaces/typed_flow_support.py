"""Shared typed-flow support used by interface adapters."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from VitalAI.application import (
    ApplicationAssembly,
    ApplicationAssemblyPolicySnapshot,
    ApplicationRuntimeDiagnostics,
    build_application_assembly_from_environment_for_role,
)
from VitalAI.application.use_cases.runtime_signal_views import build_runtime_signal_views
from VitalAI.platform.observability import ObservationRecord, ObservabilityCollector

_DEFAULT_ASSEMBLIES: dict[str, ApplicationAssembly] = {}
_DEFAULT_POLICY_ROLES: tuple[str, ...] = ("default", "api", "scheduler", "consumer")


def get_default_application_assembly(role: str = "default") -> ApplicationAssembly:
    """Build and cache the default assembly for one runtime role."""
    if role not in _DEFAULT_ASSEMBLIES:
        _DEFAULT_ASSEMBLIES[role] = build_application_assembly_from_environment_for_role(role)
    return _DEFAULT_ASSEMBLIES[role]


def get_api_application_assembly() -> ApplicationAssembly:
    """Return the shared API assembly."""
    return get_default_application_assembly(role="api")


def get_scheduler_application_assembly() -> ApplicationAssembly:
    """Return the shared scheduler assembly."""
    return get_default_application_assembly(role="scheduler")


def get_consumer_application_assembly() -> ApplicationAssembly:
    """Return the shared consumer assembly."""
    return get_default_application_assembly(role="consumer")


def get_application_policy_snapshot(role: str = "default") -> ApplicationAssemblyPolicySnapshot:
    """Return the active policy snapshot for one runtime role."""
    return get_default_application_assembly(role=role).describe_policies()


def serialize_policy_snapshot(snapshot: ApplicationAssemblyPolicySnapshot) -> dict[str, object]:
    """Serialize an assembly policy snapshot for interface responses."""
    return asdict(snapshot)


def get_application_runtime_diagnostics(role: str = "default") -> ApplicationRuntimeDiagnostics:
    """Return assembly-driven runtime diagnostics for one runtime role."""
    return get_default_application_assembly(role=role).run_runtime_diagnostics()


def get_application_health_failover_drill(role: str = "default") -> ApplicationRuntimeDiagnostics:
    """Return a controlled health-critical failover drill for one runtime role."""
    return get_default_application_assembly(role=role).run_health_critical_failover_drill()


def runtime_controls_enabled(role: str = "default") -> bool:
    """Return whether side-effecting runtime control endpoints are enabled."""
    return get_default_application_assembly(role=role).runtime_control_enabled


def build_policy_observation(role: str = "default") -> ObservationRecord:
    """Translate one role policy snapshot into an observation record."""
    snapshot = get_application_policy_snapshot(role)
    return ObservabilityCollector().record_policy_snapshot(
        runtime_role=snapshot.runtime_role,
        reporting_enabled=snapshot.reporting_enabled,
        reporting_policy_source=snapshot.reporting_policy_source,
        runtime_signals_enabled=snapshot.runtime_signals_enabled,
        runtime_signals_policy_source=snapshot.runtime_signals_policy_source,
        require_ack_override=snapshot.require_ack_override,
        ttl_override=snapshot.ttl_override,
        ingress_policy_source=snapshot.ingress_policy_source,
        trace_id=f"policy-{snapshot.runtime_role}",
    )


def serialize_observation_record(record: ObservationRecord) -> dict[str, object]:
    """Serialize one observation record for interface responses."""
    return {
        "observation_id": record.observation_id,
        "source": record.source,
        "kind": record.kind.value,
        "severity": record.severity.value,
        "summary": record.summary,
        "trace_id": record.trace_id,
        "observed_at": record.observed_at.isoformat(),
        "attributes": dict(record.attributes),
    }


def serialize_workflow_result(result: Any) -> dict[str, object]:
    """Serialize the shared shape of a workflow result."""
    runtime_signals = [asdict(item) for item in result.runtime_signals]
    return {
        "accepted": result.flow_result.accepted,
        "event_type": None if result.flow_result.summary is None else result.flow_result.summary.event_type,
        "decision_type": None
        if result.flow_result.outcome is None
        else result.flow_result.outcome.decision_message.msg_type,
        "feedback_report": None if result.feedback_report is None else asdict(result.feedback_report),
        "runtime_signals": runtime_signals,
    }


def serialize_profile_memory_workflow_result(result: Any) -> dict[str, object]:
    """Serialize the profile-memory workflow shape including persisted state."""
    payload = serialize_workflow_result(result)
    outcome = result.flow_result.outcome
    if outcome is None:
        payload["stored_entry"] = None
        payload["profile_snapshot"] = None
        return payload

    payload["stored_entry"] = asdict(outcome.stored_entry)
    payload["profile_snapshot"] = serialize_profile_memory_snapshot(outcome.profile_snapshot)
    return payload


def serialize_daily_life_workflow_result(result: Any) -> dict[str, object]:
    """Serialize the daily-life workflow shape including persisted history."""
    payload = serialize_workflow_result(result)
    outcome = result.flow_result.outcome
    if outcome is None:
        payload["checkin_entry"] = None
        payload["daily_life_snapshot"] = None
        return payload

    payload["checkin_entry"] = None if outcome.history_entry is None else asdict(outcome.history_entry)
    payload["daily_life_snapshot"] = (
        None if outcome.history_snapshot is None else serialize_daily_life_checkin_snapshot(outcome.history_snapshot)
    )
    return payload


def serialize_health_workflow_result(result: Any) -> dict[str, object]:
    """Serialize the health workflow shape including persisted history."""
    payload = serialize_workflow_result(result)
    outcome = result.flow_result.outcome
    if outcome is None:
        payload["health_alert_entry"] = None
        payload["health_alert_snapshot"] = None
        return payload

    payload["health_alert_entry"] = None if outcome.history_entry is None else asdict(outcome.history_entry)
    payload["health_alert_snapshot"] = (
        None if outcome.history_snapshot is None else serialize_health_alert_snapshot(outcome.history_snapshot)
    )
    return payload


def serialize_mental_care_workflow_result(result: Any) -> dict[str, object]:
    """Serialize the mental-care workflow shape including persisted history."""
    payload = serialize_workflow_result(result)
    outcome = result.flow_result.outcome
    if outcome is None:
        payload["mental_care_entry"] = None
        payload["mental_care_snapshot"] = None
        return payload

    payload["mental_care_entry"] = None if outcome.history_entry is None else asdict(outcome.history_entry)
    payload["mental_care_snapshot"] = (
        None if outcome.history_snapshot is None else serialize_mental_care_checkin_snapshot(outcome.history_snapshot)
    )
    return payload


def serialize_health_query_result(result: Any) -> dict[str, object]:
    """Serialize a read-only health alert history query workflow result."""
    snapshot = result.query_result.snapshot
    return {
        "accepted": result.query_result.accepted,
        "user_id": snapshot.user_id,
        "health_alert_snapshot": serialize_health_alert_snapshot(snapshot),
    }


def serialize_health_alert_snapshot(snapshot: Any) -> dict[str, object]:
    """Serialize one health alert history read model."""
    return {
        "user_id": snapshot.user_id,
        "alert_count": snapshot.alert_count,
        "recent_risk_levels": list(snapshot.recent_risk_levels),
        "readable_summary": snapshot.readable_summary,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }


def serialize_mental_care_query_result(result: Any) -> dict[str, object]:
    """Serialize a read-only mental-care history query workflow result."""
    snapshot = result.query_result.snapshot
    return {
        "accepted": result.query_result.accepted,
        "user_id": snapshot.user_id,
        "mental_care_snapshot": serialize_mental_care_checkin_snapshot(snapshot),
    }


def serialize_mental_care_checkin_snapshot(snapshot: Any) -> dict[str, object]:
    """Serialize one mental-care check-in history read model."""
    return {
        "user_id": snapshot.user_id,
        "checkin_count": snapshot.checkin_count,
        "recent_mood_signals": list(snapshot.recent_mood_signals),
        "recent_support_needs": list(snapshot.recent_support_needs),
        "readable_summary": snapshot.readable_summary,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }


def serialize_daily_life_query_result(result: Any) -> dict[str, object]:
    """Serialize a read-only daily-life history query workflow result."""
    snapshot = result.query_result.snapshot
    return {
        "accepted": result.query_result.accepted,
        "user_id": snapshot.user_id,
        "daily_life_snapshot": serialize_daily_life_checkin_snapshot(snapshot),
    }


def serialize_daily_life_checkin_snapshot(snapshot: Any) -> dict[str, object]:
    """Serialize one daily-life check-in history read model."""
    return {
        "user_id": snapshot.user_id,
        "checkin_count": snapshot.checkin_count,
        "recent_needs": list(snapshot.recent_needs),
        "readable_summary": snapshot.readable_summary,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }


def serialize_profile_memory_query_result(result: Any) -> dict[str, object]:
    """Serialize a read-only profile-memory query workflow result."""
    outcome = result.query_result.outcome
    return {
        "accepted": result.query_result.accepted,
        "user_id": outcome.profile_snapshot.user_id,
        "profile_snapshot": serialize_profile_memory_snapshot(outcome.profile_snapshot),
    }


def serialize_profile_memory_snapshot(snapshot: Any) -> dict[str, object]:
    """Serialize one profile-memory snapshot read model."""
    return {
        "user_id": snapshot.user_id,
        "memory_count": snapshot.memory_count,
        "memory_keys": list(snapshot.memory_keys),
        "readable_summary": snapshot.readable_summary,
        "entries": [asdict(entry) for entry in snapshot.entries],
    }


def serialize_runtime_diagnostics(result: ApplicationRuntimeDiagnostics) -> dict[str, object]:
    """Serialize assembly-driven runtime diagnostics for interface responses."""
    runtime_signals = [asdict(item) for item in result.runtime_signals]
    return {
        "runtime_role": result.runtime_role,
        "snapshot_id": result.snapshot_id,
        "failover_triggered": result.failover_triggered,
        "active_node": result.active_node,
        "interrupt_action": result.interrupt_action,
        "interrupt_has_snapshot_refs": result.interrupt_has_snapshot_refs,
        "latest_security_action": result.latest_security_action,
        "latest_security_finding_count": result.latest_security_finding_count,
        "latest_security_highest_severity": result.latest_security_highest_severity,
        "latest_failover_signal_id": result.latest_failover_signal_id,
        "runtime_signals": runtime_signals,
    }


def serialize_user_interaction_result(result: Any) -> dict[str, object]:
    """Serialize the backend-only user interaction result shape."""
    return {
        "accepted": result.accepted,
        "event_type": result.event_type,
        "routed_event_type": result.routed_event_type,
        "user_id": result.user_id,
        "channel": result.channel,
        "response": result.response,
        "actions": list(result.actions),
        "runtime_signals": [asdict(item) for item in result.runtime_signals],
        "memory_updates": dict(result.memory_updates),
        "session": dict(result.session),
        "preprocessing": dict(result.preprocessing),
        "intent": dict(result.intent),
        "error": result.error,
        "error_details": dict(result.error_details),
    }


def get_application_policy_matrix(
    roles: tuple[str, ...] = _DEFAULT_POLICY_ROLES,
) -> dict[str, dict[str, object]]:
    """Return serialized policy snapshots for a group of standard roles."""
    return {
        role: serialize_policy_snapshot(get_application_policy_snapshot(role))
        for role in roles
    }


def build_health_workflow(role: str = "default") -> Any:
    """Build the health workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_health_workflow()


def build_health_alert_history_query_workflow(role: str = "default") -> Any:
    """Build the health alert history query workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_health_alert_history_query_workflow()


def build_daily_life_workflow(role: str = "default") -> Any:
    """Build the daily-life workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_daily_life_workflow()


def build_daily_life_checkin_history_query_workflow(role: str = "default") -> Any:
    """Build the daily-life history query workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_daily_life_checkin_history_query_workflow()


def build_mental_care_workflow(role: str = "default") -> Any:
    """Build the mental-care workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_mental_care_workflow()


def build_mental_care_checkin_history_query_workflow(role: str = "default") -> Any:
    """Build the mental-care history query workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_mental_care_checkin_history_query_workflow()


def build_profile_memory_workflow(role: str = "default") -> Any:
    """Build the profile-memory workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_profile_memory_workflow()


def build_profile_memory_query_workflow(role: str = "default") -> Any:
    """Build the profile-memory query workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_profile_memory_query_workflow()


def build_user_interaction_workflow(role: str = "default") -> Any:
    """Build the backend-only interaction workflow through the shared default assembly."""
    return get_default_application_assembly(role=role).build_user_interaction_workflow()
