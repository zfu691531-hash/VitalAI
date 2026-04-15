"""Tests for the profile-memory application flow."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from VitalAI.application import build_application_assembly_from_environment_for_role
from VitalAI.application.commands import ProfileMemoryUpdateCommand
from VitalAI.application.queries import ProfileMemorySnapshotQuery


class ProfileMemoryFlowTests(unittest.TestCase):
    def test_profile_memory_workflow_persists_and_updates_entries(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "profile-memory.sqlite3"
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")

                first = assembly.build_profile_memory_workflow().run(
                    ProfileMemoryUpdateCommand(
                        source_agent="profile-flow",
                        trace_id="trace-profile-flow-1",
                        user_id="elder-1501",
                        memory_key="favorite_drink",
                        memory_value="ginger_tea",
                    )
                )
                second = assembly.build_profile_memory_workflow().run(
                    ProfileMemoryUpdateCommand(
                        source_agent="profile-flow",
                        trace_id="trace-profile-flow-2",
                        user_id="elder-1501",
                        memory_key="favorite_drink",
                        memory_value="barley_tea",
                    )
                )
                stored_entry = assembly.profile_memory_repository.get_memory(
                    user_id="elder-1501",
                    memory_key="favorite_drink",
                )
                db_file_existed = db_path.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(first.flow_result.accepted)
        self.assertTrue(second.flow_result.accepted)
        self.assertIsNotNone(first.feedback_report)
        self.assertIsNotNone(second.feedback_report)
        self.assertTrue(db_file_existed)
        self.assertIsNotNone(stored_entry)
        self.assertEqual("barley_tea", stored_entry.memory_value)
        self.assertEqual("favorite_drink", second.flow_result.outcome.stored_entry.memory_key)
        self.assertEqual("barley_tea", second.flow_result.outcome.stored_entry.memory_value)
        self.assertEqual(1, second.flow_result.outcome.profile_snapshot.memory_count)
        self.assertEqual(
            "barley_tea",
            second.flow_result.outcome.profile_snapshot.entries[0].memory_value,
        )

    def test_profile_memory_query_workflow_reads_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-query-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "profile-memory.sqlite3"
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")

                assembly.build_profile_memory_workflow().run(
                    ProfileMemoryUpdateCommand(
                        source_agent="profile-flow",
                        trace_id="trace-profile-query-write",
                        user_id="elder-1502",
                        memory_key="breakfast_preference",
                        memory_value="oatmeal",
                    )
                )
                result = assembly.build_profile_memory_query_workflow().run(
                    ProfileMemorySnapshotQuery(
                        source_agent="profile-query",
                        trace_id="trace-profile-query-read",
                        user_id="elder-1502",
                    )
                )
                empty_result = assembly.build_profile_memory_query_workflow().run(
                    ProfileMemorySnapshotQuery(
                        source_agent="profile-query",
                        trace_id="trace-profile-query-empty",
                        user_id="elder-unknown",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual("elder-1502", result.query_result.outcome.profile_snapshot.user_id)
        self.assertEqual(1, result.query_result.outcome.profile_snapshot.memory_count)
        self.assertEqual(
            "oatmeal",
            result.query_result.outcome.profile_snapshot.entries[0].memory_value,
        )
        self.assertTrue(empty_result.query_result.accepted)
        self.assertEqual("elder-unknown", empty_result.query_result.outcome.profile_snapshot.user_id)
        self.assertEqual(0, empty_result.query_result.outcome.profile_snapshot.memory_count)
