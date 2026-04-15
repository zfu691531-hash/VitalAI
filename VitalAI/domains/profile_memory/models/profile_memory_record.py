"""Base-backed persistence model for profile-memory records."""

from __future__ import annotations

from pydantic import Field

from Base.Repository.base.baseDBModel import BaseDBModel


class ProfileMemoryRecordModel(BaseDBModel):
    """SQLite-backed table model used by the profile-memory repository."""

    table_alias = "profile_memory_records"
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS {{table_name}} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        memory_key TEXT NOT NULL,
        memory_value TEXT NOT NULL,
        source_agent TEXT NOT NULL,
        trace_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, memory_key)
    )
    """

    id: int | None = Field(default=None, description="Primary key")
    user_id: str
    memory_key: str
    memory_value: str
    source_agent: str
    trace_id: str
    created_at: str
    updated_at: str
