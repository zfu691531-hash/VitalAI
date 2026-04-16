"""Base-backed persistence model for daily-life check-in records."""

from __future__ import annotations

from pydantic import Field

from Base.Repository.base.baseDBModel import BaseDBModel


class DailyLifeCheckInRecordModel(BaseDBModel):
    """SQLite-backed table model used by the daily-life history repository."""

    table_alias = "daily_life_checkin_records"
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS {{table_name}} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        need TEXT NOT NULL,
        urgency TEXT NOT NULL,
        source_agent TEXT NOT NULL,
        trace_id TEXT NOT NULL,
        message_id TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """

    id: int | None = Field(default=None, description="Primary key")
    user_id: str
    need: str
    urgency: str
    source_agent: str
    trace_id: str
    message_id: str
    created_at: str
