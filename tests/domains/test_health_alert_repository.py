"""Tests for health alert repository persistence and transitions."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
import shutil
from uuid import uuid4

from VitalAI.domains.health import (
    HealthAlertNotFoundError,
    HealthAlertRepository,
    HealthAlertStatusTransitionError,
)


class HealthAlertRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        self.temp_dir = runtime_dir / f"health-repository-{uuid4().hex}"
        self.temp_dir.mkdir()
        self.db_path = self.temp_dir / "health.sqlite3"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_alert_defaults_to_raised_and_exposes_alert_id(self) -> None:
        repository = HealthAlertRepository(database_path=str(self.db_path))

        entry = repository.add_alert(
            user_id="elder-9001",
            risk_level="high",
            source_agent="test-agent",
            trace_id="trace-health-repo-create",
            message_id="msg-health-repo-create",
        )

        self.assertGreater(entry.alert_id, 0)
        self.assertEqual("raised", entry.status)
        self.assertEqual(entry.created_at, entry.updated_at)

    def test_transition_alert_status_updates_entry_and_snapshot(self) -> None:
        repository = HealthAlertRepository(database_path=str(self.db_path))
        created = repository.add_alert(
            user_id="elder-9002",
            risk_level="critical",
            source_agent="test-agent",
            trace_id="trace-health-repo-transition-create",
            message_id="msg-health-repo-transition-create",
        )

        updated, previous_status = repository.transition_alert_status(
            user_id="elder-9002",
            alert_id=created.alert_id,
            target_status="acknowledged",
            source_agent="test-agent",
            trace_id="trace-health-repo-transition-ack",
        )

        snapshot = repository.get_snapshot(user_id="elder-9002")

        self.assertEqual("raised", previous_status)
        self.assertEqual("acknowledged", updated.status)
        self.assertNotEqual(updated.created_at, updated.updated_at)
        self.assertEqual(["acknowledged"], snapshot.recent_statuses)

    def test_get_filtered_snapshot_returns_only_matching_status(self) -> None:
        repository = HealthAlertRepository(database_path=str(self.db_path))
        first = repository.add_alert(
            user_id="elder-9002b",
            risk_level="high",
            source_agent="test-agent",
            trace_id="trace-health-repo-filter-first",
            message_id="msg-health-repo-filter-first",
        )
        second = repository.add_alert(
            user_id="elder-9002b",
            risk_level="critical",
            source_agent="test-agent",
            trace_id="trace-health-repo-filter-second",
            message_id="msg-health-repo-filter-second",
        )
        repository.transition_alert_status(
            user_id="elder-9002b",
            alert_id=first.alert_id,
            target_status="acknowledged",
            source_agent="test-agent",
            trace_id="trace-health-repo-filter-ack",
        )

        snapshot = repository.get_filtered_snapshot(
            user_id="elder-9002b",
            status_filter="acknowledged",
        )

        self.assertEqual(1, snapshot.alert_count)
        self.assertEqual([first.alert_id], [entry.alert_id for entry in snapshot.entries])
        self.assertEqual(["acknowledged"], snapshot.recent_statuses)
        self.assertEqual(second.alert_id, repository.get_alert(user_id="elder-9002b", alert_id=second.alert_id).alert_id)

    def test_transition_alert_status_rejects_invalid_transition(self) -> None:
        repository = HealthAlertRepository(database_path=str(self.db_path))
        created = repository.add_alert(
            user_id="elder-9003",
            risk_level="high",
            source_agent="test-agent",
            trace_id="trace-health-repo-invalid-create",
            message_id="msg-health-repo-invalid-create",
        )
        repository.transition_alert_status(
            user_id="elder-9003",
            alert_id=created.alert_id,
            target_status="resolved",
            source_agent="test-agent",
            trace_id="trace-health-repo-invalid-resolve",
        )

        with self.assertRaises(HealthAlertStatusTransitionError):
            repository.transition_alert_status(
                user_id="elder-9003",
                alert_id=created.alert_id,
                target_status="acknowledged",
                source_agent="test-agent",
                trace_id="trace-health-repo-invalid-ack",
            )

    def test_transition_alert_status_raises_for_missing_alert(self) -> None:
        repository = HealthAlertRepository(database_path=str(self.db_path))

        with self.assertRaises(HealthAlertNotFoundError):
            repository.transition_alert_status(
                user_id="elder-missing",
                alert_id=404,
                target_status="resolved",
                source_agent="test-agent",
                trace_id="trace-health-repo-missing",
            )

    def test_repository_migrates_legacy_table_shape(self) -> None:
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                """
                CREATE TABLE health_alert_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    source_agent TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    message_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO health_alert_records (
                    user_id,
                    risk_level,
                    source_agent,
                    trace_id,
                    message_id,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "elder-legacy",
                    "high",
                    "legacy-agent",
                    "trace-health-repo-legacy",
                    "msg-health-repo-legacy",
                    "2026-04-17T00:00:00+00:00",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        repository = HealthAlertRepository(database_path=str(self.db_path))

        snapshot = repository.get_snapshot(user_id="elder-legacy")

        self.assertEqual(1, snapshot.alert_count)
        self.assertEqual("raised", snapshot.entries[0].status)
        self.assertEqual("2026-04-17T00:00:00+00:00", snapshot.entries[0].updated_at)
