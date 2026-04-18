"""Tests for the daily-life history application flow."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from VitalAI.application import (
    DailyLifeCheckInCommand,
    DailyLifeCheckInHistoryQuery,
    build_application_assembly_from_environment_for_role,
)


class DailyLifeHistoryFlowTests(unittest.TestCase):
    def test_daily_life_workflow_persists_recent_checkins(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-history-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "daily-life.sqlite3"
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_daily_life_workflow()

                first = workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-history-meal",
                        user_id="elder-1801",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                second = workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-history-mobility",
                        user_id="elder-1801",
                        need="mobility_support",
                        urgency="high",
                    )
                )
                snapshot = assembly.daily_life_repository.get_snapshot(user_id="elder-1801")
                db_file_existed = db_path.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(first.flow_result.accepted)
        self.assertTrue(second.flow_result.accepted)
        self.assertTrue(db_file_existed)
        self.assertIsNotNone(second.flow_result.outcome.history_entry)
        self.assertEqual("mobility_support", second.flow_result.outcome.history_entry.need)
        self.assertIsNotNone(second.flow_result.outcome.history_snapshot)
        self.assertEqual(2, second.flow_result.outcome.history_snapshot.checkin_count)
        self.assertEqual(["mobility_support", "meal_support"], snapshot.recent_needs)
        self.assertEqual(
            "2 daily-life check-ins: mobility_support, meal_support",
            snapshot.readable_summary,
        )

    def test_daily_life_history_query_workflow_reads_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-query-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "daily-life.sqlite3"
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_daily_life_workflow()

                workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-query-meal",
                        user_id="elder-1802",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-query-mobility",
                        user_id="elder-1802",
                        need="mobility_support",
                        urgency="high",
                    )
                )
                result = assembly.build_daily_life_checkin_history_query_workflow().run(
                    DailyLifeCheckInHistoryQuery(
                        source_agent="daily-query",
                        trace_id="trace-daily-query-read",
                        user_id="elder-1802",
                        limit=1,
                    )
                )
                empty_result = assembly.build_daily_life_checkin_history_query_workflow().run(
                    DailyLifeCheckInHistoryQuery(
                        source_agent="daily-query",
                        trace_id="trace-daily-query-empty",
                        user_id="elder-empty",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual("elder-1802", result.query_result.snapshot.user_id)
        self.assertEqual(1, result.query_result.snapshot.checkin_count)
        self.assertEqual(["mobility_support"], result.query_result.snapshot.recent_needs)
        self.assertEqual("high", result.query_result.snapshot.entries[0].urgency)
        self.assertTrue(empty_result.query_result.accepted)
        self.assertEqual(0, empty_result.query_result.snapshot.checkin_count)
        self.assertEqual(
            "No daily-life check-ins for elder-empty.",
            empty_result.query_result.snapshot.readable_summary,
        )



    def test_daily_life_history_query_normalizes_non_positive_limit(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-query-limit-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "daily-life.sqlite3"
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_daily_life_workflow()

                workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-limit-meal",
                        user_id="elder-1803",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                workflow.run(
                    DailyLifeCheckInCommand(
                        source_agent="daily-flow",
                        trace_id="trace-daily-limit-mobility",
                        user_id="elder-1803",
                        need="mobility_support",
                        urgency="high",
                    )
                )
                result = assembly.build_daily_life_checkin_history_query_workflow().run(
                    DailyLifeCheckInHistoryQuery(
                        source_agent="daily-query",
                        trace_id="trace-daily-limit-read",
                        user_id="elder-1803",
                        limit=0,
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual(1, result.query_result.snapshot.checkin_count)
        self.assertEqual(["mobility_support"], result.query_result.snapshot.recent_needs)

if __name__ == "__main__":
    unittest.main()
