"""Typed runtime-signal views exposed by application-facing flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from VitalAI.platform.observability import ObservationRecord


@dataclass(slots=True)
class RuntimeSignalView:
    """Small typed runtime-signal view safe to expose to interfaces."""

    kind: str
    severity: str
    source: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def runtime_signal_view_from_observation(record: ObservationRecord) -> RuntimeSignalView:
    """Convert one observation record into the application runtime-signal view."""
    return RuntimeSignalView(
        kind=record.kind.value,
        severity=record.severity.value,
        source=record.source,
        summary=record.summary,
        details=_select_runtime_signal_details(record),
    )


def build_runtime_signal_views(records: list[ObservationRecord]) -> list[RuntimeSignalView]:
    """Convert raw observation records into small typed runtime-signal views."""
    return [runtime_signal_view_from_observation(record) for record in records]


def _select_runtime_signal_details(record: ObservationRecord) -> dict[str, object]:
    """Return the stable detail subset exposed by runtime-signal views."""
    attributes = record.attributes
    if record.kind.value == "EVENT_SUMMARY":
        return {
            "event_type": attributes.get("event_type"),
            "priority": attributes.get("priority"),
            "target_agent": attributes.get("target_agent"),
        }
    if record.kind.value == "SECURITY_REVIEW":
        return {
            "signal_type": attributes.get("signal_type"),
            "action": attributes.get("action"),
            "finding_count": attributes.get("finding_count"),
            "highest_severity": attributes.get("highest_severity"),
        }
    if record.kind.value == "INTERRUPT_SIGNAL":
        return {
            "action": attributes.get("action"),
            "priority": attributes.get("priority"),
            "target": attributes.get("target"),
            "has_snapshot_refs": attributes.get("has_snapshot_refs"),
        }
    if record.kind.value == "RUNTIME_SNAPSHOT":
        return {
            "snapshot_id": attributes.get("snapshot_id"),
            "version": attributes.get("version"),
        }
    if record.kind.value == "FAILOVER_TRANSITION":
        return {
            "previous_node": attributes.get("previous_node"),
            "current_node": attributes.get("current_node"),
            "signal_id": attributes.get("signal_id"),
            "has_snapshot_refs": attributes.get("has_snapshot_refs"),
            "snapshot_ids": attributes.get("snapshot_ids"),
        }
    return {}
