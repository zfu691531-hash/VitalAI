"""Application query object for one lightweight user overview."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserOverviewQuery:
    """Read-only query that aggregates existing user-facing snapshots."""

    source_agent: str
    trace_id: str
    user_id: str
    history_limit: int = 3
    memory_key: str = ""
