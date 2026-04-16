"""Tests for the health alert history application flow."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from VitalAI.application import (
    HealthAlertCommand,
    HealthAlertHistoryQuery,
    build_application_assembly_from_environment_for_role,
)


class HealthAlertHistoryFlowTests(unittest.TestCase):
    def test_health_workflow_persists_recent_alerts(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-history-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "health.sqlite3"
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_health_workflow()

                first = workflow.run(
                    HealthAlertCommand(
                        source_agent="health-flow",
                        trace_id="trace-health-history-high",
                        user_id="elder-1901",
                        risk_level="high",
                    )
                )
                second = workflow.run(
                    HealthAlertCommand(
                        source_agent="health-flow",
                        trace_id="trace-health-history-critical",
                        user_id="elder-1901",
                        risk_level="critical",
                    )
                )
                snapshot = assembly.health_repository.get_snapshot(user_id="elder-1901")
                db_file_existed = db_path.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(first.flow_result.accepted)
        self.assertTrue(second.flow_result.accepted)
        self.assertTrue(db_file_existed)
        self.assertIsNotNone(second.flow_result.outcome.history_entry)
        self.assertEqual("critical", second.flow_result.outcome.history_entry.risk_level)
        self.assertIsNotNone(second.flow_result.outcome.history_snapshot)
        self.assertEqual(2, second.flow_result.outcome.history_snapshot.alert_count)
        self.assertEqual(["critical", "high"], snapshot.recent_risk_levels)
        self.assertEqual(
            "2 health alerts: critical, high",
            snapshot.readable_summary,
        )

    def test_health_history_query_workflow_reads_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-query-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "health.sqlite3"
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_health_workflow()

                workflow.run(
                    HealthAlertCommand(
                        source_agent="health-flow",
                        trace_id="trace-health-query-high",
                        user_id="elder-1902",
                        risk_level="high",
                    )
                )
                workflow.run(
                    HealthAlertCommand(
                        source_agent="health-flow",
                        trace_id="trace-health-query-critical",
                        user_id="elder-1902",
                        risk_level="critical",
                    )
                )
                result = assembly.build_health_alert_history_query_workflow().run(
                    HealthAlertHistoryQuery(
                        source_agent="health-query",
                        trace_id="trace-health-query-read",
                        user_id="elder-1902",
                        limit=1,
                    )
                )
                empty_result = assembly.build_health_alert_history_query_workflow().run(
                    HealthAlertHistoryQuery(
                        source_agent="health-query",
                        trace_id="trace-health-query-empty",
                        user_id="elder-empty",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.query_result.accepted)
        self.assertEqual("elder-1902", result.query_result.snapshot.user_id)
        self.assertEqual(1, result.query_result.snapshot.alert_count)
        self.assertEqual(["critical"], result.query_result.snapshot.recent_risk_levels)
        self.assertEqual("critical", result.query_result.snapshot.entries[0].risk_level)
        self.assertTrue(empty_result.query_result.accepted)
        self.assertEqual(0, empty_result.query_result.snapshot.alert_count)
        self.assertEqual(
            "No health alerts for elder-empty.",
            empty_result.query_result.snapshot.readable_summary,
        )


if __name__ == "__main__":
    unittest.main()
