"""Application use case for a lightweight aggregated user overview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from VitalAI.application.queries import (
    DailyLifeCheckInHistoryQuery,
    HealthAlertHistoryQuery,
    MentalCareCheckInHistoryQuery,
    ProfileMemorySnapshotQuery,
    UserOverviewQuery,
)
from VitalAI.domains.daily_life import DailyLifeCheckInSnapshot
from VitalAI.domains.health import HealthAlertSnapshot
from VitalAI.domains.mental_care import MentalCareCheckInSnapshot
from VitalAI.domains.profile_memory import ProfileMemorySnapshot


@dataclass(slots=True)
class UserOverviewQueryResult:
    """Aggregated read-only result for one user overview request."""

    accepted: bool
    user_id: str
    history_limit: int
    latest_activity_at: str | None
    recent_activity: list["UserOverviewActivityItem"]
    attention_summary: str
    attention_items: list["UserOverviewAttentionItem"]
    profile_memory_snapshot: ProfileMemorySnapshot
    health_alert_snapshot: HealthAlertSnapshot
    daily_life_snapshot: DailyLifeCheckInSnapshot
    mental_care_snapshot: MentalCareCheckInSnapshot


@dataclass(slots=True)
class UserOverviewActivityItem:
    """One lightweight cross-domain timeline item shown in the user overview."""

    domain: str
    item_id: str
    occurred_at: str
    summary: str


@dataclass(slots=True)
class UserOverviewAttentionItem:
    """One lightweight attention hint derived from the current domain snapshots."""

    domain: str
    item_id: str
    severity: str
    summary: str


@dataclass
class RunUserOverviewQueryUseCase:
    """Compose the existing domain query workflows into one overview response."""

    health_query_workflow: Any
    daily_life_query_workflow: Any
    mental_care_query_workflow: Any
    profile_memory_query_workflow: Any

    def run(self, query: UserOverviewQuery) -> UserOverviewQueryResult:
        """Load the existing read-model snapshots needed for one user overview."""
        health_result = self.health_query_workflow.run(
            HealthAlertHistoryQuery(
                source_agent=query.source_agent,
                trace_id=f"{query.trace_id}:health",
                user_id=query.user_id,
                limit=query.history_limit,
            )
        )
        daily_life_result = self.daily_life_query_workflow.run(
            DailyLifeCheckInHistoryQuery(
                source_agent=query.source_agent,
                trace_id=f"{query.trace_id}:daily_life",
                user_id=query.user_id,
                limit=query.history_limit,
            )
        )
        mental_care_result = self.mental_care_query_workflow.run(
            MentalCareCheckInHistoryQuery(
                source_agent=query.source_agent,
                trace_id=f"{query.trace_id}:mental_care",
                user_id=query.user_id,
                limit=query.history_limit,
            )
        )
        profile_memory_result = self.profile_memory_query_workflow.run(
            ProfileMemorySnapshotQuery(
                source_agent=query.source_agent,
                trace_id=f"{query.trace_id}:profile_memory",
                user_id=query.user_id,
                memory_key=query.memory_key,
            )
        )

        recent_activity = _build_recent_activity(
            profile_memory_snapshot=profile_memory_result.query_result.outcome.profile_snapshot,
            health_alert_snapshot=health_result.query_result.snapshot,
            daily_life_snapshot=daily_life_result.query_result.snapshot,
            mental_care_snapshot=mental_care_result.query_result.snapshot,
        )
        attention_items = _build_attention_items(
            health_alert_snapshot=health_result.query_result.snapshot,
            daily_life_snapshot=daily_life_result.query_result.snapshot,
            mental_care_snapshot=mental_care_result.query_result.snapshot,
        )
        return UserOverviewQueryResult(
            accepted=(
                health_result.query_result.accepted
                and daily_life_result.query_result.accepted
                and mental_care_result.query_result.accepted
                and profile_memory_result.query_result.accepted
            ),
            user_id=query.user_id,
            history_limit=query.history_limit,
            latest_activity_at=None if not recent_activity else recent_activity[0].occurred_at,
            recent_activity=recent_activity,
            attention_summary=_build_attention_summary(query.user_id, attention_items),
            attention_items=attention_items,
            profile_memory_snapshot=profile_memory_result.query_result.outcome.profile_snapshot,
            health_alert_snapshot=health_result.query_result.snapshot,
            daily_life_snapshot=daily_life_result.query_result.snapshot,
            mental_care_snapshot=mental_care_result.query_result.snapshot,
        )


def _build_recent_activity(
    *,
    profile_memory_snapshot: ProfileMemorySnapshot,
    health_alert_snapshot: HealthAlertSnapshot,
    daily_life_snapshot: DailyLifeCheckInSnapshot,
    mental_care_snapshot: MentalCareCheckInSnapshot,
) -> list[UserOverviewActivityItem]:
    """Flatten the existing snapshots into one lightweight cross-domain timeline."""
    items = [
        *[
            UserOverviewActivityItem(
                domain="profile_memory",
                item_id=entry.memory_key,
                occurred_at=entry.updated_at,
                summary=f"Memory {entry.memory_key}={entry.memory_value}",
            )
            for entry in profile_memory_snapshot.entries
        ],
        *[
            UserOverviewActivityItem(
                domain="health",
                item_id=str(entry.alert_id),
                occurred_at=entry.updated_at,
                summary=f"Health alert {entry.risk_level} ({entry.status})",
            )
            for entry in health_alert_snapshot.entries
        ],
        *[
            UserOverviewActivityItem(
                domain="daily_life",
                item_id=str(entry.checkin_id),
                occurred_at=entry.created_at,
                summary=f"Daily-life {entry.need} ({entry.urgency})",
            )
            for entry in daily_life_snapshot.entries
        ],
        *[
            UserOverviewActivityItem(
                domain="mental_care",
                item_id=str(entry.checkin_id),
                occurred_at=entry.created_at,
                summary=f"Mental-care {entry.mood_signal} ({entry.support_need})",
            )
            for entry in mental_care_snapshot.entries
        ],
    ]
    return sorted(items, key=lambda item: _parse_iso_datetime(item.occurred_at), reverse=True)


def _parse_iso_datetime(value: str) -> datetime:
    """Parse one persisted ISO timestamp for stable cross-domain ordering."""
    return datetime.fromisoformat(value)


def _build_attention_items(
    *,
    health_alert_snapshot: HealthAlertSnapshot,
    daily_life_snapshot: DailyLifeCheckInSnapshot,
    mental_care_snapshot: MentalCareCheckInSnapshot,
) -> list[UserOverviewAttentionItem]:
    """Derive a few lightweight attention hints without adding any new workflow logic."""
    items = [
        *[
            UserOverviewAttentionItem(
                domain="health",
                item_id=str(entry.alert_id),
                severity=entry.risk_level,
                summary=f"Health alert {entry.risk_level} is still {entry.status}",
            )
            for entry in health_alert_snapshot.entries
            if entry.status != "resolved"
        ],
        *[
            UserOverviewAttentionItem(
                domain="daily_life",
                item_id=str(entry.checkin_id),
                severity=entry.urgency,
                summary=f"Daily-life need {entry.need} is marked {entry.urgency}",
            )
            for entry in daily_life_snapshot.entries
            if entry.urgency == "high"
        ],
        *[
            UserOverviewAttentionItem(
                domain="mental_care",
                item_id=str(entry.checkin_id),
                severity="medium",
                summary=f"Mental-care mood {entry.mood_signal} may need follow-up",
            )
            for entry in mental_care_snapshot.entries
            if entry.mood_signal in {"distressed", "anxious", "sad"}
        ],
    ]
    return items


def _build_attention_summary(user_id: str, items: list[UserOverviewAttentionItem]) -> str:
    """Render a concise human-readable summary for manual overview checks."""
    if not items:
        return f"No immediate attention items for {user_id}."
    return f"{len(items)} attention item(s) for {user_id}."
