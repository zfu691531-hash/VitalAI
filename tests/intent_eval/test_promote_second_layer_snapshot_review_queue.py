"""Tests for promoting approved review-queue items into the replay dataset."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from uuid import uuid4

from scripts.intent_eval.promote_second_layer_snapshot_review_queue import (
    ROOT_DIR,
    build_promoted_snapshot_dataset,
    format_promotion_summary,
    load_review_queue,
    write_snapshot_dataset,
)
from scripts.intent_eval.evaluate_second_layer_hard_cases import evaluate_samples, load_samples


class PromoteSecondLayerSnapshotReviewQueueTests(unittest.TestCase):
    def test_build_promoted_dataset_selects_only_approved_items(self) -> None:
        dataset = build_promoted_snapshot_dataset(
            [
                {
                    "id": "snap_new",
                    "category": "snapshot_route",
                    "description": "approved",
                    "raw_response_text": "{\"status\":\"hold_for_human_review\",\"ready_for_routing\":false,\"routing_decision\":\"reject\",\"primary_task\":null,\"secondary_tasks\":[],\"risk_flags\":[],\"notes\":\"x\"}",
                    "expected": {"valid": True, "guard_status": "rejected_by_second_layer", "blocked_reasons": ["second_layer_reject"]},
                    "review_status": "approved_for_baseline",
                    "review_notes": "looks good",
                    "review_recommendation": "approve_candidate",
                    "review_recommendation_reasons": ["guard_status:rejected_by_second_layer"],
                    "bulk_approval_recommendation": "eligible_for_bulk_approval",
                    "bulk_approval_recommendation_reasons": ["guard_status:rejected_by_second_layer"],
                    "source_capture": {"model": "glm-5.1"},
                },
                {
                    "id": "snap_skip",
                    "category": "snapshot_route",
                    "raw_response_text": "{}",
                    "expected": {"valid": False},
                    "review_status": "pending_human_review",
                },
            ],
            existing_items=[
                {
                    "id": "snap_existing",
                    "category": "snapshot_existing",
                    "raw_response_text": "{}",
                    "expected": {"valid": False},
                }
            ],
        )

        self.assertEqual(2, len(dataset))
        self.assertEqual(["snap_existing", "snap_new"], [item["id"] for item in dataset])
        self.assertEqual("approved_for_baseline", dataset[1]["review_metadata"]["review_status"])
        self.assertEqual("approve_candidate", dataset[1]["review_metadata"]["review_recommendation"])
        self.assertEqual("eligible_for_bulk_approval", dataset[1]["review_metadata"]["bulk_approval_recommendation"])

    def test_promoted_dataset_can_be_replayed_by_eval_script(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"snapshot-promote-test-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            dataset_path = temp_dir / "promoted.jsonl"
            write_snapshot_dataset(
                [
                    {
                        "id": "snap_route",
                        "category": "snapshot_route",
                        "description": "approved route",
                        "raw_response_text": (
                            "{"
                            "\"status\":\"decomposed\","
                            "\"ready_for_routing\":true,"
                            "\"routing_decision\":\"route_primary\","
                            "\"primary_task\":{\"task_type\":\"memory_update\",\"intent\":\"profile_memory_update\","
                            "\"priority\":40,\"confidence\":0.8},"
                            "\"secondary_tasks\":[],"
                            "\"risk_flags\":[],"
                            "\"notes\":\"ok\""
                            "}"
                        ),
                        "expected": {
                            "valid": True,
                            "guard_status": "routing_candidate",
                            "blocked_reasons": [],
                        },
                    }
                ],
                dataset_path,
            )

            summary = evaluate_samples(load_samples(dataset_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(1, summary["total_samples"])
        self.assertEqual(0, summary["expectation_failure_count"])

    def test_cli_promotes_approved_items_into_dataset(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"snapshot-promote-cli-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            queue_path = temp_dir / "review-queue.jsonl"
            queue_path.write_text(
                (
                    "{\"id\":\"snap_approved\",\"category\":\"snapshot_parse_failure\","
                    "\"raw_response_text\":\"not json\","
                    "\"expected\":{\"valid\":false,\"parse_error_contains\":\"valid JSON object\"},"
                    "\"review_status\":\"approved_for_baseline\",\"review_notes\":\"ok\"}\n"
                    "{\"id\":\"snap_pending\",\"category\":\"snapshot_parse_failure\","
                    "\"raw_response_text\":\"not json\","
                    "\"expected\":{\"valid\":false},"
                    "\"review_status\":\"pending_human_review\"}\n"
                ),
                encoding="utf-8",
            )
            output_path = temp_dir / "promoted.jsonl"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/promote_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            promoted = load_review_queue(output_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("approved_promoted: 1", completed.stdout)
        self.assertEqual(1, len(promoted))
        self.assertEqual("snap_approved", promoted[0]["id"])

    def test_format_promotion_summary_reports_counts(self) -> None:
        text = format_promotion_summary(
            [{"id": "a"}, {"id": "b"}],
            Path("data") / "intent_eval" / "second_layer_response_snapshots.jsonl",
            approved_count=1,
            skipped_count=3,
        )

        self.assertIn("dataset_items: 2", text)
        self.assertIn("approved_promoted: 1", text)
        self.assertIn("skipped_items: 3", text)


if __name__ == "__main__":
    unittest.main()
