"""Tests for daily-life check-in repository persistence and queries."""

from __future__ import annotations

import unittest
from pathlib import Path
import shutil
from uuid import uuid4

from VitalAI.domains.daily_life import (
    DailyLifeCheckInNotFoundError,
    DailyLifeCheckInRepository,
)


class DailyLifeCheckInRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        self.temp_dir = runtime_dir / f"daily-life-repository-{uuid4().hex}"
        self.temp_dir.mkdir()
        self.db_path = self.temp_dir / "daily_life.sqlite3"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_checkin_exposes_checkin_id(self) -> None:
        repository = DailyLifeCheckInRepository(database_path=str(self.db_path))

        entry = repository.add_checkin(
            user_id="elder-dl-1",
            need="meal_support",
            urgency="normal",
            source_agent="test-agent",
            trace_id="trace-daily-repo-create",
            message_id="msg-daily-repo-create",
        )

        self.assertGreater(entry.checkin_id, 0)
        self.assertEqual("meal_support", entry.need)

    def test_get_filtered_snapshot_returns_only_matching_urgency(self) -> None:
        repository = DailyLifeCheckInRepository(database_path=str(self.db_path))
        normal = repository.add_checkin(
            user_id="elder-dl-2",
            need="meal_support",
            urgency="normal",
            source_agent="test-agent",
            trace_id="trace-daily-repo-normal",
            message_id="msg-daily-repo-normal",
        )
        repository.add_checkin(
            user_id="elder-dl-2",
            need="mobility_support",
            urgency="high",
            source_agent="test-agent",
            trace_id="trace-daily-repo-high",
            message_id="msg-daily-repo-high",
        )

        snapshot = repository.get_filtered_snapshot(
            user_id="elder-dl-2",
            urgency_filter="normal",
        )

        self.assertEqual(1, snapshot.checkin_count)
        self.assertEqual([normal.checkin_id], [entry.checkin_id for entry in snapshot.entries])
        self.assertEqual(["meal_support"], snapshot.recent_needs)

    def test_get_checkin_raises_for_missing_entry(self) -> None:
        repository = DailyLifeCheckInRepository(database_path=str(self.db_path))

        with self.assertRaises(DailyLifeCheckInNotFoundError):
            repository.get_checkin(user_id="elder-missing", checkin_id=404)


if __name__ == "__main__":
    unittest.main()
