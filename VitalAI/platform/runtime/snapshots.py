"""Snapshot runtime primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from VitalAI.platform.interrupt import SnapshotReference
from VitalAI.platform.messaging import MessagePriority

if TYPE_CHECKING:
    from VitalAI.platform.runtime.event_aggregator import EventSummary
    from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass
class RuntimeSnapshot:
    """Runtime snapshot used for takeover and recovery."""

    snapshot_id: str
    created_at: datetime
    source: str
    payload: dict[str, Any]
    trace_id: str | None = None
    version: int = 1

    def to_reference(self) -> SnapshotReference:
        """Build an interrupt-facing reference for this snapshot."""
        return SnapshotReference(
            snapshot_id=self.snapshot_id,
            source=self.source,
            captured_at=self.created_at,
            version=self.version,
        )


@dataclass(frozen=True, slots=True)
class SnapshotCaptureDecision:
    """Typed decision describing why a runtime snapshot should be captured."""

    policy_name: str
    reason: str
    interrupt_reason: str


@dataclass(frozen=True, slots=True)
class SnapshotCaptureRule:
    """Small typed rule deciding whether one event summary should emit a snapshot."""

    event_type: str
    policy_name: str
    reason: str
    interrupt_reason: str
    priority: MessagePriority | None = None
    payload_matches: dict[str, object] = field(default_factory=dict)

    def matches(self, summary: "EventSummary") -> bool:
        """Return whether this rule applies to the current event summary."""
        if summary.event_type != self.event_type:
            return False
        if self.priority is not None and summary.priority is not self.priority:
            return False
        return all(summary.payload.get(key) == value for key, value in self.payload_matches.items())

    def decide(self) -> SnapshotCaptureDecision:
        """Build the typed capture decision for this rule."""
        return SnapshotCaptureDecision(
            policy_name=self.policy_name,
            reason=self.reason,
            interrupt_reason=self.interrupt_reason,
        )


@dataclass(frozen=True, slots=True)
class SnapshotCapturePolicy:
    """Typed runtime snapshot policy made of small explicit rules."""

    rules: tuple[SnapshotCaptureRule, ...]

    def decide(self, summary: "EventSummary") -> SnapshotCaptureDecision | None:
        """Return the first matching snapshot-capture decision for one summary."""
        for rule in self.rules:
            if rule.matches(summary):
                return rule.decide()
        return None


DEFAULT_RUNTIME_SNAPSHOT_POLICY = SnapshotCapturePolicy(
    rules=(
        SnapshotCaptureRule(
            event_type="HEALTH_ALERT",
            priority=MessagePriority.CRITICAL,
            policy_name="critical_health_alert",
            reason="critical health alert requires runtime snapshot capture",
            interrupt_reason="critical health alert captured runtime snapshot for takeover readiness",
        ),
        SnapshotCaptureRule(
            event_type="DAILY_LIFE_CHECKIN",
            priority=MessagePriority.CRITICAL,
            payload_matches={"urgency": "high"},
            policy_name="high_urgency_daily_life_checkin",
            reason="high urgency daily-life check-in requires runtime snapshot capture",
            interrupt_reason="high urgency daily-life check-in captured runtime snapshot for takeover readiness",
        ),
    )
)


@dataclass
class SnapshotStore:
    """Minimal in-memory snapshot store."""

    snapshots: dict[str, RuntimeSnapshot] = field(default_factory=dict)
    snapshot_versions: dict[tuple[str, int], RuntimeSnapshot] = field(default_factory=dict)

    def save(
        self,
        snapshot_id: str,
        source: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> RuntimeSnapshot:
        """Save a snapshot and return the stored object."""
        previous_snapshot = self.snapshots.get(snapshot_id)
        snapshot = RuntimeSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(UTC),
            source=source,
            payload=payload,
            trace_id=trace_id,
            version=1 if previous_snapshot is None else previous_snapshot.version + 1,
        )
        self.snapshots[snapshot_id] = snapshot
        self.snapshot_versions[(snapshot_id, snapshot.version)] = snapshot
        if signal_bridge is not None:
            signal_bridge.observe_snapshot(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> RuntimeSnapshot | None:
        """Return a snapshot by identifier."""
        return self.snapshots.get(snapshot_id)

    def get_reference(self, snapshot_id: str) -> SnapshotReference | None:
        """Return a snapshot reference by identifier."""
        snapshot = self.get(snapshot_id)
        if snapshot is None:
            return None
        return snapshot.to_reference()

    def get_version(self, snapshot_id: str, version: int) -> RuntimeSnapshot | None:
        """Return one historical snapshot version by identifier and version."""
        return self.snapshot_versions.get((snapshot_id, version))

    def latest(self) -> RuntimeSnapshot | None:
        """Return the most recently created snapshot."""
        if not self.snapshots:
            return None
        return max(self.snapshots.values(), key=lambda item: item.created_at)


def _default_snapshot_store_path() -> Path:
    """Return the default local path for persisted runtime snapshots."""
    return Path.cwd() / ".runtime" / "runtime_snapshots.json"


@dataclass
class FileSnapshotStore(SnapshotStore):
    """File-backed snapshot store for local development persistence."""

    storage_path: str | Path = field(default_factory=_default_snapshot_store_path)

    def __post_init__(self) -> None:
        """Load any previously persisted snapshot history."""
        self.storage_path = self._resolve_storage_path(self.storage_path)
        self._load()

    def save(
        self,
        snapshot_id: str,
        source: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> RuntimeSnapshot:
        """Save a snapshot, persist history, and return the stored object."""
        snapshot = super().save(
            snapshot_id=snapshot_id,
            source=source,
            payload=payload,
            trace_id=trace_id,
            signal_bridge=signal_bridge,
        )
        self._persist()
        return snapshot

    def _load(self) -> None:
        """Load snapshot history from disk when the file exists."""
        path = Path(self.storage_path)
        if not path.exists():
            return

        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        records = content.get("snapshots", [])
        if not isinstance(records, list):
            return

        for record in records:
            snapshot = self._snapshot_from_record(record)
            if snapshot is None:
                continue
            self.snapshot_versions[(snapshot.snapshot_id, snapshot.version)] = snapshot
            current_latest = self.snapshots.get(snapshot.snapshot_id)
            if current_latest is None or snapshot.version >= current_latest.version:
                self.snapshots[snapshot.snapshot_id] = snapshot

    def _persist(self) -> None:
        """Persist all known snapshot versions to disk."""
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        records = [
            self._snapshot_to_record(snapshot)
            for _, snapshot in sorted(
                self.snapshot_versions.items(),
                key=lambda item: (item[0][0], item[0][1]),
            )
        ]
        payload = {"snapshots": records}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _resolve_storage_path(storage_path: str | Path) -> Path:
        """Resolve the configured snapshot store path."""
        path = Path(storage_path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return path

    @staticmethod
    def _snapshot_to_record(snapshot: RuntimeSnapshot) -> dict[str, Any]:
        """Serialize one snapshot into a JSON-compatible record."""
        return {
            "snapshot_id": snapshot.snapshot_id,
            "created_at": snapshot.created_at.isoformat(),
            "source": snapshot.source,
            "payload": snapshot.payload,
            "trace_id": snapshot.trace_id,
            "version": snapshot.version,
        }

    @staticmethod
    def _snapshot_from_record(record: object) -> RuntimeSnapshot | None:
        """Deserialize one snapshot record, ignoring malformed entries."""
        if not isinstance(record, dict):
            return None
        try:
            created_at = datetime.fromisoformat(str(record["created_at"]))
            payload = record.get("payload", {})
            if not isinstance(payload, dict):
                payload = {"value": payload}
            return RuntimeSnapshot(
                snapshot_id=str(record["snapshot_id"]),
                created_at=created_at,
                source=str(record["source"]),
                payload=payload,
                trace_id=None if record.get("trace_id") is None else str(record["trace_id"]),
                version=int(record.get("version", 1)),
            )
        except (KeyError, TypeError, ValueError):
            return None
