"""Health alert repository built on Base SQLite primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Final

from Base.Repository.connections.sqliteConnection import SQLiteConnection
from VitalAI.domains.health.models import (
    HealthAlertEntry,
    HealthAlertRecordModel,
    HealthAlertSnapshot,
    HealthAlertStatus,
)

_HEALTH_ALERT_STATUS_TRANSITIONS: Final[dict[str, set[str]]] = {
    HealthAlertStatus.RAISED.value: {
        HealthAlertStatus.ACKNOWLEDGED.value,
        HealthAlertStatus.RESOLVED.value,
    },
    HealthAlertStatus.ACKNOWLEDGED.value: {HealthAlertStatus.RESOLVED.value},
    HealthAlertStatus.RESOLVED.value: set(),
}


class HealthAlertNotFoundError(LookupError):
    """Raised when one requested health alert record does not exist."""


class HealthAlertStatusTransitionError(ValueError):
    """Raised when one health alert status transition is not allowed."""


def _project_root() -> Path:
    """Resolve the repository root from the current working directory."""
    return Path.cwd()


def _default_health_db_path() -> Path:
    """Return the default persistent SQLite file for health alert history."""
    return _project_root() / ".runtime" / "health.sqlite3"


def _normalize_limit(limit: int) -> int:
    """Keep read-side limits small and predictable."""
    if limit < 1:
        return 1
    if limit > 100:
        return 100
    return limit


def _normalize_status_filter(status_filter: str) -> str:
    """Keep optional status filters stable and lowercase."""
    return status_filter.strip().lower()


@dataclass
class HealthAlertRepository:
    """Repository responsible for health alert history persistence."""

    database_path: str | None = None
    _connection: SQLiteConnection | None = field(default=None, init=False, repr=False)

    def add_alert(
        self,
        *,
        user_id: str,
        risk_level: str,
        source_agent: str,
        trace_id: str,
        message_id: str,
    ) -> HealthAlertEntry:
        """Persist one health alert entry, idempotent by message id."""
        self._bind_model_connection()

        existing = HealthAlertRecordModel.find_one_by(message_id=message_id)
        if existing is not None:
            return self._to_entry(existing)

        now = datetime.now(UTC).isoformat()
        record = HealthAlertRecordModel(
            user_id=user_id,
            risk_level=risk_level,
            status=HealthAlertStatus.RAISED.value,
            source_agent=source_agent,
            trace_id=trace_id,
            message_id=message_id,
            created_at=now,
            updated_at=now,
        )
        record.save()
        return self._to_entry(record)

    def transition_alert_status(
        self,
        *,
        user_id: str,
        alert_id: int,
        target_status: str,
        source_agent: str,
        trace_id: str,
    ) -> tuple[HealthAlertEntry, str]:
        """Move one alert to the next allowed status and return the updated entry."""
        self._bind_model_connection()

        normalized_target_status = target_status.strip().lower()
        if normalized_target_status not in {
            HealthAlertStatus.RAISED.value,
            HealthAlertStatus.ACKNOWLEDGED.value,
            HealthAlertStatus.RESOLVED.value,
        }:
            raise HealthAlertStatusTransitionError(
                f"Unsupported health alert status transition target: {target_status}"
            )

        record = HealthAlertRecordModel.find_one_by(id=alert_id, user_id=user_id)
        if record is None:
            raise HealthAlertNotFoundError(
                f"Health alert {alert_id} for user {user_id} was not found."
            )

        previous_status = record.status
        allowed_targets = _HEALTH_ALERT_STATUS_TRANSITIONS.get(previous_status, set())
        if normalized_target_status not in allowed_targets:
            raise HealthAlertStatusTransitionError(
                f"Health alert {alert_id} cannot transition from {previous_status} to {normalized_target_status}."
            )

        record.update(
            status=normalized_target_status,
            source_agent=source_agent,
            trace_id=trace_id,
            updated_at=datetime.now(UTC).isoformat(),
        )
        refreshed = HealthAlertRecordModel.get_by_id(alert_id)
        if refreshed is None:
            raise HealthAlertNotFoundError(
                f"Health alert {alert_id} for user {user_id} disappeared after update."
            )
        return self._to_entry(refreshed), previous_status

    def get_snapshot(self, *, user_id: str, limit: int = 20) -> HealthAlertSnapshot:
        """Load recent health alerts for one user."""
        self._bind_model_connection()
        records = self._find_records(
            user_id=user_id,
            limit=limit,
        )
        return HealthAlertSnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def get_filtered_snapshot(
        self,
        *,
        user_id: str,
        status_filter: str = "",
        limit: int = 20,
    ) -> HealthAlertSnapshot:
        """Load recent health alerts for one user, optionally filtered by status."""
        self._bind_model_connection()
        records = self._find_records(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
        )
        return HealthAlertSnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def get_alert(self, *, user_id: str, alert_id: int) -> HealthAlertEntry:
        """Load one persisted health alert entry by user and alert id."""
        self._bind_model_connection()
        record = HealthAlertRecordModel.find_one_by(id=alert_id, user_id=user_id)
        if record is None:
            raise HealthAlertNotFoundError(
                f"Health alert {alert_id} for user {user_id} was not found."
            )
        return self._to_entry(record)

    def _find_records(
        self,
        *,
        user_id: str,
        status_filter: str = "",
        limit: int = 20,
    ) -> list[HealthAlertRecordModel]:
        """Return persisted records for one user with an optional status filter."""
        normalized_status_filter = _normalize_status_filter(status_filter)
        filters: dict[str, object] = {"user_id": user_id}
        if normalized_status_filter:
            filters["status"] = normalized_status_filter
        return HealthAlertRecordModel.find_by(
            limit=_normalize_limit(limit),
            order_by="id",
            order="DESC",
            **filters,
        )

    def _bind_model_connection(self) -> None:
        """Ensure the BaseDBModel class is bound to this repository connection."""
        connection = self._ensure_connection()
        if HealthAlertRecordModel._db_connection is connection:
            self._ensure_schema()
            return
        HealthAlertRecordModel.set_db_connection(connection)
        HealthAlertRecordModel._table_checked = False
        self._ensure_schema()

    def _ensure_connection(self) -> SQLiteConnection:
        """Create and cache the repository SQLite connection."""
        if self._connection is None:
            self._connection = SQLiteConnection(database=self._resolve_database_path())
        return self._connection

    def _ensure_schema(self) -> None:
        """Keep legacy SQLite files compatible with the current health alert schema."""
        connection = self._ensure_connection()
        if not connection.table_exists(HealthAlertRecordModel.get_table_name()):
            return

        columns = {
            row["name"]
            for row in connection.execute_query(
                f"PRAGMA table_info({HealthAlertRecordModel.get_table_name()})"
            )
        }
        if "status" not in columns:
            connection.execute_update(
                f"ALTER TABLE {HealthAlertRecordModel.get_table_name()} "
                "ADD COLUMN status TEXT NOT NULL DEFAULT 'raised'"
            )
        if "updated_at" not in columns:
            connection.execute_update(
                f"ALTER TABLE {HealthAlertRecordModel.get_table_name()} "
                "ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
            )
            connection.execute_update(
                f"UPDATE {HealthAlertRecordModel.get_table_name()} "
                "SET updated_at = created_at WHERE updated_at = ''"
            )

    def _resolve_database_path(self) -> str:
        """Resolve the configured SQLite location and create parent dirs when needed."""
        configured_path = self.database_path
        if configured_path is None:
            configured_path = os.getenv("VITALAI_HEALTH_DB_PATH")

        normalized = "" if configured_path is None else configured_path.strip()
        if normalized == "":
            normalized = str(_default_health_db_path())
        if normalized == ":memory:":
            return normalized

        path = Path(normalized).expanduser()
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def _to_entry(record: HealthAlertRecordModel) -> HealthAlertEntry:
        """Translate one persistence record into a stable domain entry."""
        return HealthAlertEntry(
            alert_id=int(record.id or -1),
            user_id=record.user_id,
            risk_level=record.risk_level,
            status=record.status,
            source_agent=record.source_agent,
            trace_id=record.trace_id,
            message_id=record.message_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
