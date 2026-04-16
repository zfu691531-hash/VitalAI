"""Mental-care check-in repository built on Base SQLite primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from pathlib import Path

from Base.Repository.connections.sqliteConnection import SQLiteConnection
from VitalAI.domains.mental_care.models import (
    MentalCareCheckInEntry,
    MentalCareCheckInRecordModel,
    MentalCareCheckInSnapshot,
)


def _project_root() -> Path:
    """Resolve the repository root from the current working directory."""
    return Path.cwd()


def _default_mental_care_db_path() -> Path:
    """Return the default persistent SQLite file for mental-care history."""
    return _project_root() / ".runtime" / "mental_care.sqlite3"


def _normalize_limit(limit: int) -> int:
    """Keep read-side limits small and predictable."""
    if limit < 1:
        return 1
    if limit > 100:
        return 100
    return limit


@dataclass
class MentalCareCheckInRepository:
    """Repository responsible for mental-care check-in history persistence."""

    database_path: str | None = None
    _connection: SQLiteConnection | None = field(default=None, init=False, repr=False)

    def add_checkin(
        self,
        *,
        user_id: str,
        mood_signal: str,
        support_need: str,
        source_agent: str,
        trace_id: str,
        message_id: str,
    ) -> MentalCareCheckInEntry:
        """Persist one check-in entry, idempotent by message id."""
        self._bind_model_connection()

        existing = MentalCareCheckInRecordModel.find_one_by(message_id=message_id)
        if existing is not None:
            return self._to_entry(existing)

        record = MentalCareCheckInRecordModel(
            user_id=user_id,
            mood_signal=mood_signal,
            support_need=support_need,
            source_agent=source_agent,
            trace_id=trace_id,
            message_id=message_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        record.save()
        return self._to_entry(record)

    def get_snapshot(self, *, user_id: str, limit: int = 20) -> MentalCareCheckInSnapshot:
        """Load recent mental-care check-ins for one user."""
        self._bind_model_connection()
        records = MentalCareCheckInRecordModel.find_by(
            user_id=user_id,
            limit=_normalize_limit(limit),
            order_by="id",
            order="DESC",
        )
        return MentalCareCheckInSnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def _bind_model_connection(self) -> None:
        """Ensure the BaseDBModel class is bound to this repository connection."""
        connection = self._ensure_connection()
        if MentalCareCheckInRecordModel._db_connection is connection:
            return
        MentalCareCheckInRecordModel.set_db_connection(connection)
        MentalCareCheckInRecordModel._table_checked = False

    def _ensure_connection(self) -> SQLiteConnection:
        """Create and cache the repository SQLite connection."""
        if self._connection is None:
            self._connection = SQLiteConnection(database=self._resolve_database_path())
        return self._connection

    def _resolve_database_path(self) -> str:
        """Resolve the configured SQLite location and create parent dirs when needed."""
        configured_path = self.database_path
        if configured_path is None:
            configured_path = os.getenv("VITALAI_MENTAL_CARE_DB_PATH")

        normalized = "" if configured_path is None else configured_path.strip()
        if normalized == "":
            normalized = str(_default_mental_care_db_path())
        if normalized == ":memory:":
            return normalized

        path = Path(normalized).expanduser()
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def _to_entry(record: MentalCareCheckInRecordModel) -> MentalCareCheckInEntry:
        """Translate one persistence record into a stable domain entry."""
        return MentalCareCheckInEntry(
            user_id=record.user_id,
            mood_signal=record.mood_signal,
            support_need=record.support_need,
            source_agent=record.source_agent,
            trace_id=record.trace_id,
            message_id=record.message_id,
            created_at=record.created_at,
        )
