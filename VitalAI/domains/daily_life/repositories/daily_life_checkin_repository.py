"""Daily-life check-in repository built on Base SQLite primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from pathlib import Path

from Base.Repository.connections.sqliteConnection import SQLiteConnection
from VitalAI.domains.daily_life.models import (
    DailyLifeCheckInEntry,
    DailyLifeCheckInRecordModel,
    DailyLifeCheckInSnapshot,
)


class DailyLifeCheckInNotFoundError(LookupError):
    """Raised when one requested daily-life check-in record does not exist."""


def _project_root() -> Path:
    """Resolve the repository root from the current working directory."""
    return Path.cwd()


def _default_daily_life_db_path() -> Path:
    """Return the default persistent SQLite file for daily-life history."""
    return _project_root() / ".runtime" / "daily_life.sqlite3"


def _normalize_limit(limit: int) -> int:
    """Keep read-side limits small and predictable."""
    if limit < 1:
        return 1
    if limit > 100:
        return 100
    return limit


def _normalize_urgency_filter(urgency_filter: str) -> str:
    """Keep optional urgency filters stable and lowercase."""
    return urgency_filter.strip().lower()


@dataclass
class DailyLifeCheckInRepository:
    """Repository responsible for daily-life check-in history persistence."""

    database_path: str | None = None
    _connection: SQLiteConnection | None = field(default=None, init=False, repr=False)

    def add_checkin(
        self,
        *,
        user_id: str,
        need: str,
        urgency: str,
        source_agent: str,
        trace_id: str,
        message_id: str,
    ) -> DailyLifeCheckInEntry:
        """Persist one check-in entry, idempotent by message id."""
        self._bind_model_connection()

        existing = DailyLifeCheckInRecordModel.find_one_by(message_id=message_id)
        if existing is not None:
            return self._to_entry(existing)

        record = DailyLifeCheckInRecordModel(
            user_id=user_id,
            need=need,
            urgency=urgency,
            source_agent=source_agent,
            trace_id=trace_id,
            message_id=message_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        record.save()
        return self._to_entry(record)

    def get_snapshot(self, *, user_id: str, limit: int = 20) -> DailyLifeCheckInSnapshot:
        """Load recent daily-life check-ins for one user."""
        self._bind_model_connection()
        records = self._find_records(user_id=user_id, limit=limit)
        return DailyLifeCheckInSnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def get_filtered_snapshot(
        self,
        *,
        user_id: str,
        urgency_filter: str = "",
        limit: int = 20,
    ) -> DailyLifeCheckInSnapshot:
        """Load recent daily-life check-ins for one user, optionally filtered by urgency."""
        self._bind_model_connection()
        records = self._find_records(
            user_id=user_id,
            urgency_filter=urgency_filter,
            limit=limit,
        )
        return DailyLifeCheckInSnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def get_checkin(self, *, user_id: str, checkin_id: int) -> DailyLifeCheckInEntry:
        """Load one persisted daily-life check-in entry by user and check-in id."""
        self._bind_model_connection()
        record = DailyLifeCheckInRecordModel.find_one_by(id=checkin_id, user_id=user_id)
        if record is None:
            raise DailyLifeCheckInNotFoundError(
                f"Daily-life check-in {checkin_id} for user {user_id} was not found."
            )
        return self._to_entry(record)

    def _find_records(
        self,
        *,
        user_id: str,
        urgency_filter: str = "",
        limit: int = 20,
    ) -> list[DailyLifeCheckInRecordModel]:
        """Return persisted records for one user with an optional urgency filter."""
        normalized_urgency_filter = _normalize_urgency_filter(urgency_filter)
        filters: dict[str, object] = {"user_id": user_id}
        if normalized_urgency_filter:
            filters["urgency"] = normalized_urgency_filter
        return DailyLifeCheckInRecordModel.find_by(
            limit=_normalize_limit(limit),
            order_by="id",
            order="DESC",
            **filters,
        )

    def _bind_model_connection(self) -> None:
        """Ensure the BaseDBModel class is bound to this repository connection."""
        connection = self._ensure_connection()
        if DailyLifeCheckInRecordModel._db_connection is connection:
            return
        DailyLifeCheckInRecordModel.set_db_connection(connection)
        DailyLifeCheckInRecordModel._table_checked = False

    def _ensure_connection(self) -> SQLiteConnection:
        """Create and cache the repository SQLite connection."""
        if self._connection is None:
            self._connection = SQLiteConnection(database=self._resolve_database_path())
        return self._connection

    def _resolve_database_path(self) -> str:
        """Resolve the configured SQLite location and create parent dirs when needed."""
        configured_path = self.database_path
        if configured_path is None:
            configured_path = os.getenv("VITALAI_DAILY_LIFE_DB_PATH")

        normalized = "" if configured_path is None else configured_path.strip()
        if normalized == "":
            normalized = str(_default_daily_life_db_path())
        if normalized == ":memory:":
            return normalized

        path = Path(normalized).expanduser()
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def _to_entry(record: DailyLifeCheckInRecordModel) -> DailyLifeCheckInEntry:
        """Translate one persistence record into a stable domain entry."""
        return DailyLifeCheckInEntry(
            checkin_id=int(record.id or -1),
            user_id=record.user_id,
            need=record.need,
            urgency=record.urgency,
            source_agent=record.source_agent,
            trace_id=record.trace_id,
            message_id=record.message_id,
            created_at=record.created_at,
        )
