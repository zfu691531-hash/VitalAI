"""Tests for mental-care check-in repository persistence and queries."""

from __future__ import annotations

import unittest
from pathlib import Path
import shutil
from uuid import uuid4

from VitalAI.domains.mental_care import (
    MentalCareCheckInNotFoundError,
    MentalCareCheckInRepository,
)


class MentalCareCheckInRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        self.temp_dir = runtime_dir / f"mental-care-repository-{uuid4().hex}"
        self.temp_dir.mkdir()
        self.db_path = self.temp_dir / "mental_care.sqlite3"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_checkin_exposes_checkin_id(self) -> None:
        repository = MentalCareCheckInRepository(database_path=str(self.db_path))

        entry = repository.add_checkin(
            user_id="elder-mc-1",
            mood_signal="calm",
            support_need="companionship",
            source_agent="test-agent",
            trace_id="trace-mental-repo-create",
            message_id="msg-mental-repo-create",
        )

        self.assertGreater(entry.checkin_id, 0)
        self.assertEqual("calm", entry.mood_signal)

    def test_get_filtered_snapshot_returns_only_matching_mood(self) -> None:
        repository = MentalCareCheckInRepository(database_path=str(self.db_path))
        calm = repository.add_checkin(
            user_id="elder-mc-2",
            mood_signal="calm",
            support_need="companionship",
            source_agent="test-agent",
            trace_id="trace-mental-repo-calm",
            message_id="msg-mental-repo-calm",
        )
        repository.add_checkin(
            user_id="elder-mc-2",
            mood_signal="distressed",
            support_need="reassurance",
            source_agent="test-agent",
            trace_id="trace-mental-repo-distressed",
            message_id="msg-mental-repo-distressed",
        )

        snapshot = repository.get_filtered_snapshot(
            user_id="elder-mc-2",
            mood_filter="calm",
        )

        self.assertEqual(1, snapshot.checkin_count)
        self.assertEqual([calm.checkin_id], [entry.checkin_id for entry in snapshot.entries])
        self.assertEqual(["calm"], snapshot.recent_mood_signals)

    def test_get_checkin_raises_for_missing_entry(self) -> None:
        repository = MentalCareCheckInRepository(database_path=str(self.db_path))

        with self.assertRaises(MentalCareCheckInNotFoundError):
            repository.get_checkin(user_id="elder-missing", checkin_id=404)


if __name__ == "__main__":
    unittest.main()
