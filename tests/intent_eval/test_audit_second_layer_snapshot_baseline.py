"""Tests for auditing the promoted second-layer snapshot baseline dataset."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from uuid import uuid4

from scripts.intent_eval.audit_second_layer_snapshot_baseline import (
    ROOT_DIR,
    audit_snapshot_dataset,
    format_audit_report,
    load_snapshot_dataset,
)


class AuditSecondLayerSnapshotBaselineTests(unittest.TestCase):
    def test_audit_snapshot_dataset_counts_provenance(self) -> None:
        summary = audit_snapshot_dataset(
            [
                {
                    "id": "snap_1",
                    "category": "snapshot_route",
                    "expected": {"valid": True, "guard_status": "routing_candidate"},
                    "review_metadata": {
                        "review_status": "approved_for_baseline",
                        "review_recommendation": "approve_candidate",
                        "bulk_approval_recommendation": "eligible_for_bulk_approval",
                        "source_capture": {"model": "glm-5.1"},
                    },
                },
                {
                    "id": "snap_2",
                    "category": "snapshot_parse_failure",
                    "expected": {"valid": False},
                    "review_metadata": {
                        "review_status": "approved_for_baseline",
                        "review_recommendation": "baseline_negative_candidate",
                        "bulk_approval_recommendation": "not_applicable_for_bulk_approval",
                        "source_capture": {"model": "glm-5.1"},
                    },
                },
            ]
        )

        self.assertEqual(2, summary["total_items"])
        self.assertEqual(1, summary["category_counts"]["snapshot_route"])
        self.assertEqual(1, summary["expected_valid_counts"]["valid"])
        self.assertEqual(1, summary["expected_valid_counts"]["invalid"])
        self.assertEqual(2, summary["review_status_counts"]["approved_for_baseline"])
        self.assertEqual(1, summary["review_recommendation_counts"]["approve_candidate"])
        self.assertEqual(1, summary["bulk_approval_counts"]["eligible_for_bulk_approval"])
        self.assertEqual([], summary["missing_review_metadata_ids"])
        self.assertEqual([], summary["missing_source_capture_ids"])

    def test_audit_snapshot_dataset_reports_missing_metadata_and_duplicates(self) -> None:
        summary = audit_snapshot_dataset(
            [
                {
                    "id": "snap_dup",
                    "category": "snapshot_route",
                    "expected": {"valid": True},
                },
                {
                    "id": "snap_dup",
                    "category": "snapshot_route",
                    "expected": {"valid": True},
                    "review_metadata": {
                        "review_status": "approved_for_baseline",
                        "review_recommendation": "approve_candidate",
                        "bulk_approval_recommendation": "eligible_for_bulk_approval",
                    },
                },
            ]
        )

        self.assertEqual(["snap_dup"], summary["duplicate_ids"])
        self.assertEqual(["snap_dup"], summary["missing_review_metadata_ids"])
        self.assertEqual(["snap_dup"], summary["missing_source_capture_ids"])

    def test_format_audit_report_is_human_readable(self) -> None:
        text = format_audit_report(
            {
                "total_items": 2,
                "category_counts": {"snapshot_route": 2},
                "expected_valid_counts": {"valid": 2},
                "expected_guard_counts": {"routing_candidate": 2},
                "review_status_counts": {"approved_for_baseline": 2},
                "review_recommendation_counts": {"approve_candidate": 2},
                "bulk_approval_counts": {"eligible_for_bulk_approval": 2},
                "duplicate_ids": [],
                "missing_review_metadata_ids": [],
                "missing_source_capture_ids": [],
            },
            Path("data") / "intent_eval" / "second_layer_response_snapshots.jsonl",
        )

        self.assertIn("VitalAI second-layer snapshot baseline audit: OK", text)
        self.assertIn("categories: snapshot_route=2", text)
        self.assertIn("bulk_approval: eligible_for_bulk_approval=2", text)

    def test_cli_audits_snapshot_dataset(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"snapshot-audit-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            dataset_path = temp_dir / "snapshots.jsonl"
            dataset_path.write_text(
                (
                    "{\"id\":\"snap_1\",\"category\":\"snapshot_route\","
                    "\"expected\":{\"valid\":true,\"guard_status\":\"routing_candidate\"},"
                    "\"review_metadata\":{\"review_status\":\"approved_for_baseline\","
                    "\"review_recommendation\":\"approve_candidate\","
                    "\"bulk_approval_recommendation\":\"eligible_for_bulk_approval\","
                    "\"source_capture\":{\"model\":\"glm-5.1\"}}}\n"
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/audit_second_layer_snapshot_baseline.py",
                    "--dataset",
                    str(dataset_path),
                    "--output",
                    "text",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            loaded = load_snapshot_dataset(dataset_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(1, len(loaded))
        self.assertIn("VitalAI second-layer snapshot baseline audit: OK", completed.stdout)
        self.assertIn("bulk_approval: eligible_for_bulk_approval=1", completed.stdout)


if __name__ == "__main__":
    unittest.main()
