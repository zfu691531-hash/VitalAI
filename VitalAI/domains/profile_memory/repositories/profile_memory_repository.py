"""Profile-memory repository built on top of Base repository primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from pathlib import Path

from Base.Repository.connections.sqliteConnection import SQLiteConnection
from VitalAI.domains.profile_memory.models.profile_memory_entry import (
    ProfileMemoryEntry,
    ProfileMemorySnapshot,
)
from VitalAI.domains.profile_memory.models.profile_memory_record import ProfileMemoryRecordModel


def _project_root() -> Path:
    """Resolve the repository root from the current module location."""
    return Path.cwd()


def _default_profile_memory_db_path() -> Path:
    """Return the default persistent SQLite file for profile memory."""
    return _project_root() / ".runtime" / "profile_memory.sqlite3"


@dataclass
class ProfileMemoryRepository:
    """Repository responsible for long-term profile-memory persistence."""

    database_path: str | None = None
    _connection: SQLiteConnection | None = field(default=None, init=False, repr=False)

    def upsert_memory(
        self,
        *,
        user_id: str,
        memory_key: str,
        memory_value: str,
        source_agent: str,
        trace_id: str,
    ) -> ProfileMemoryEntry:
        """Insert or update one long-term profile-memory entry."""
        self._bind_model_connection()

        now = datetime.now(UTC).isoformat()
        record = ProfileMemoryRecordModel.find_one_by(user_id=user_id, memory_key=memory_key)
        if record is None:
            record = ProfileMemoryRecordModel(
                user_id=user_id,
                memory_key=memory_key,
                memory_value=memory_value,
                source_agent=source_agent,
                trace_id=trace_id,
                created_at=now,
                updated_at=now,
            )
        else:
            record.memory_value = memory_value
            record.source_agent = source_agent
            record.trace_id = trace_id
            record.updated_at = now

        record.save()
        return self._to_entry(record)

    def get_memory(
        self,
        *,
        user_id: str,
        memory_key: str,
    ) -> ProfileMemoryEntry | None:
        """Load one known memory entry by user and key."""
        self._bind_model_connection()
        record = ProfileMemoryRecordModel.find_one_by(user_id=user_id, memory_key=memory_key)
        if record is None:
            return None
        return self._to_entry(record)

    def get_snapshot(self, *, user_id: str) -> ProfileMemorySnapshot:
        """Load the current profile-memory snapshot for one user."""
        self._bind_model_connection()
        records = ProfileMemoryRecordModel.find_by(
            user_id=user_id,
            order_by="id",
            order="ASC",
        )
        return ProfileMemorySnapshot(
            user_id=user_id,
            entries=[self._to_entry(record) for record in records],
        )

    def _bind_model_connection(self) -> None:
        """Ensure the BaseDBModel class is bound to this repository connection."""
        connection = self._ensure_connection()
        if ProfileMemoryRecordModel._db_connection is connection:
            return
        ProfileMemoryRecordModel.set_db_connection(connection)
        ProfileMemoryRecordModel._table_checked = False

    def _ensure_connection(self) -> SQLiteConnection:
        """Create and cache the repository SQLite connection."""
        if self._connection is None:
            resolved_path = self._resolve_database_path()
            self._connection = SQLiteConnection(database=resolved_path)
        return self._connection

    def _resolve_database_path(self) -> str:
        """Resolve the configured SQLite location and create parent dirs when needed."""
        configured_path = self.database_path
        if configured_path is None:
            configured_path = os.getenv("VITALAI_PROFILE_MEMORY_DB_PATH")

        normalized = "" if configured_path is None else configured_path.strip()
        if normalized == "":
            normalized = str(_default_profile_memory_db_path())
        if normalized == ":memory:":
            return normalized

        path = Path(normalized).expanduser()
        if not path.is_absolute():
            path = (_project_root() / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def _to_entry(record: ProfileMemoryRecordModel) -> ProfileMemoryEntry:
        """Translate one persistence record into a stable domain entry."""
        return ProfileMemoryEntry(
            user_id=record.user_id,
            memory_key=record.memory_key,
            memory_value=record.memory_value,
            source_agent=record.source_agent,
            trace_id=record.trace_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
