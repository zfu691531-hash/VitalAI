"""Typed query used by the profile-memory read workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProfileMemorySnapshotQuery:
    """Application query for one user's current profile-memory snapshot."""

    source_agent: str
    trace_id: str
    user_id: str
    memory_key: str = ""
