"""Tests for the mental-care history application flow."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from VitalAI.application import (
    MentalCareCheckInCommand,
    MentalCareCheckInHistoryQuery,
    build_application_assembly_from_environment_for_role,
)


class MentalCareHistoryFlowTests(unittest.TestCase):
    def test_mental_care_workflow_persists_recent_checkins(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-history-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "mental-care.sqlite3"
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_mental_care_workflow()

                first = workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-history-calm",
                        user_id="elder-2001",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                second = workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-history-distressed",
                        user_id="elder-2001",
                        mood_signal="distressed",
                        support_need="emotional_checkin",
                    )
                )
                snapshot = assembly.mental_care_repository.get_snapshot(user_id="elder-2001")
                db_file_existed = db_path.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(first.flow_result.accepted)
        self.assertTrue(second.flow_result.accepted)
        self.assertTrue(db_file_existed)
        self.assertIsNotNone(second.flow_result.outcome.history_entry)
        self.assertEqual("distressed", second.flow_result.outcome.history_entry.mood_signal)
        self.assertEqual("emotional_checkin", second.flow_result.outcome.history_entry.support_need)
        self.assertIsNotNone(second.flow_result.outcome.history_snapshot)
        self.assertEqual(2, second.flow_result.outcome.history_snapshot.checkin_count)
        self.assertEqual(["distressed", "calm"], snapshot.recent_mood_signals)
        self.assertEqual(["emotional_checkin", "companionship"], snapshot.recent_support_needs)
        self.assertEqual(
            "2 mental-care check-ins: distressed, calm",
            snapshot.readable_summary,
        )

    def test_mental_care_history_query_workflow_reads_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-query-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "mental-care.sqlite3"
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_mental_care_workflow()

                workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-query-calm",
                        user_id="elder-2002",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-query-distressed",
                        user_id="elder-2002",
                        mood_signal="distressed",
                        support_need="emotional_checkin",
                    )
                )
                result = assembly.build_mental_care_checkin_history_query_workflow().run(
                    MentalCareCheckInHistoryQuery(
                        source_agent="mental-query",
                        trace_id="trace-mental-query-read",
                        user_id="elder-2002",
                        limit=1,
                    )
                )
                empty_result = assembly.build_mental_care_checkin_history_query_workflow().run(
                    MentalCareCheckInHistoryQuery(
                        source_agent="mental-query",
                        trace_id="trace-mental-query-empty",
                        user_id="elder-empty",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual("elder-2002", result.query_result.snapshot.user_id)
        self.assertEqual(1, result.query_result.snapshot.checkin_count)
        self.assertEqual(["distressed"], result.query_result.snapshot.recent_mood_signals)
        self.assertEqual("emotional_checkin", result.query_result.snapshot.entries[0].support_need)
        self.assertTrue(empty_result.query_result.accepted)
        self.assertEqual(0, empty_result.query_result.snapshot.checkin_count)
        self.assertEqual(
            "No mental-care check-ins for elder-empty.",
            empty_result.query_result.snapshot.readable_summary,
        )



    def test_mental_care_history_query_normalizes_non_positive_limit(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-query-limit-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "mental-care.sqlite3"
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_mental_care_workflow()

                workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-limit-calm",
                        user_id="elder-2003",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                workflow.run(
                    MentalCareCheckInCommand(
                        source_agent="mental-flow",
                        trace_id="trace-mental-limit-distressed",
                        user_id="elder-2003",
                        mood_signal="distressed",
                        support_need="emotional_checkin",
                    )
                )
                result = assembly.build_mental_care_checkin_history_query_workflow().run(
                    MentalCareCheckInHistoryQuery(
                        source_agent="mental-query",
                        trace_id="trace-mental-limit-read",
                        user_id="elder-2003",
                        limit=0,
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual(1, result.query_result.snapshot.checkin_count)
        self.assertEqual(["distressed"], result.query_result.snapshot.recent_mood_signals)

if __name__ == "__main__":
    unittest.main()
