"""Tests for managing second-layer snapshot review-queue items."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from uuid import uuid4

from scripts.intent_eval.manage_second_layer_snapshot_review_queue import (
    ROOT_DIR,
    filter_review_queue_items,
    find_review_queue_item,
    format_review_queue_item,
    format_review_queue_list,
    format_review_queue_report,
    format_review_queue_triage_report,
    load_review_queue,
    summarize_review_queue,
    update_review_queue_items,
    write_review_queue,
)


class ManageSecondLayerSnapshotReviewQueueTests(unittest.TestCase):
    def test_summary_counts_queue_statuses_and_categories(self) -> None:
        summary = summarize_review_queue(
            [
                {"id": "a", "category": "x", "review_status": "pending_human_review", "review_recommendation": "approve_candidate", "bulk_approval_recommendation": "eligible_for_bulk_approval"},
                {"id": "b", "category": "x", "review_status": "approved_for_baseline", "review_recommendation": "approve_candidate", "bulk_approval_recommendation": "eligible_for_bulk_approval"},
                {"id": "c", "category": "y", "review_status": "pending_human_review", "review_recommendation": "manual_review_required", "bulk_approval_recommendation": "requires_manual_approval"},
            ]
        )

        self.assertEqual(3, summary["total_items"])
        self.assertEqual(2, summary["status_counts"]["pending_human_review"])
        self.assertEqual(1, summary["status_counts"]["approved_for_baseline"])
        self.assertEqual(2, summary["category_counts"]["x"])
        self.assertEqual(2, summary["recommendation_counts"]["approve_candidate"])
        self.assertEqual(2, summary["bulk_approval_counts"]["eligible_for_bulk_approval"])

    def test_update_review_queue_items_sets_status_and_appends_notes(self) -> None:
        items = [
            {
                "id": "snap_1",
                "review_status": "pending_human_review",
                "review_notes": "first note",
            }
        ]

        update_review_queue_items(
            items,
            item_ids=["snap_1"],
            review_status="approved_for_baseline",
            review_notes="second note",
            append_notes=True,
        )

        self.assertEqual("approved_for_baseline", items[0]["review_status"])
        self.assertIn("first note\nsecond note", items[0]["review_notes"])

    def test_format_review_queue_item_can_include_raw_response(self) -> None:
        text = format_review_queue_item(
            {
                "id": "snap_1",
                "category": "snapshot_route",
                "review_status": "pending_human_review",
                "review_recommendation": "approve_candidate",
                "review_recommendation_reasons": ["guard_status:routing_candidate"],
                "bulk_approval_recommendation": "eligible_for_bulk_approval",
                "bulk_approval_recommendation_reasons": ["primary_intent:profile_memory_update"],
                "description": "route",
                "review_notes": "",
                "expected": {"valid": True},
                "raw_response_text": "{\"status\":\"decomposed\"}",
            },
            include_raw_response=True,
        )

        self.assertIn("id: snap_1", text)
        self.assertIn("raw_response_text:", text)
        self.assertIn("{\"status\":\"decomposed\"}", text)

    def test_filter_review_queue_items_can_match_validation_guard_and_parse_error(self) -> None:
        items = [
            {
                "id": "snap_valid",
                "review_status": "pending_human_review",
                "review_recommendation": "approve_candidate",
                "bulk_approval_recommendation": "eligible_for_bulk_approval",
                "category": "snapshot_route",
                "suggested_validation": {"valid": True},
                "suggested_guard": {"status": "routing_candidate"},
                "parse_error": None,
            },
            {
                "id": "snap_invalid",
                "review_status": "pending_human_review",
                "review_recommendation": "baseline_negative_candidate",
                "bulk_approval_recommendation": "not_applicable_for_bulk_approval",
                "category": "snapshot_route",
                "suggested_validation": {"valid": False},
                "suggested_guard": {"status": "blocked"},
                "parse_error": "json decode error",
            },
        ]

        valid_items = filter_review_queue_items(
            items,
            validation_state="valid",
            guard_statuses=["routing_candidate"],
            parse_error_state="no",
        )
        invalid_items = filter_review_queue_items(
            items,
            recommendations=["baseline_negative_candidate"],
            bulk_approval_recommendations=["not_applicable_for_bulk_approval"],
            validation_state="invalid",
            guard_statuses=["blocked"],
            parse_error_state="yes",
        )

        self.assertEqual(["snap_valid"], [item["id"] for item in valid_items])
        self.assertEqual(["snap_invalid"], [item["id"] for item in invalid_items])

    def test_format_review_queue_list_reports_matches(self) -> None:
        text = format_review_queue_list(
            [
                {
                    "id": "snap_1",
                    "review_status": "pending_human_review",
                    "review_recommendation": "approve_candidate",
                    "bulk_approval_recommendation": "eligible_for_bulk_approval",
                    "category": "snapshot_route",
                    "suggested_validation": {"valid": True},
                    "suggested_guard": {"status": "routing_candidate"},
                    "parse_error": None,
                }
            ],
            queue_path=Path(".runtime") / "queue.jsonl",
            limit=20,
        )

        self.assertIn("matched_items: total=1 shown=1", text)
        self.assertIn("id=snap_1", text)
        self.assertIn("recommendation=approve_candidate", text)
        self.assertIn("bulk_approval=eligible_for_bulk_approval", text)
        self.assertIn("guard=routing_candidate", text)

    def test_format_review_queue_triage_report_groups_recommendations(self) -> None:
        text = format_review_queue_triage_report(
            [
                {
                    "id": "snap_1",
                    "review_recommendation": "approve_candidate",
                    "review_recommendation_reasons": ["guard_status:routing_candidate"],
                    "bulk_approval_recommendation": "eligible_for_bulk_approval",
                    "bulk_approval_recommendation_reasons": ["primary_intent:profile_memory_update"],
                },
                {
                    "id": "snap_2",
                    "review_recommendation": "manual_review_required",
                    "review_recommendation_reasons": ["blocked_reason:high_risk:health_signal"],
                    "bulk_approval_recommendation": "requires_manual_approval",
                    "bulk_approval_recommendation_reasons": ["primary_intent:health_alert"],
                },
                {
                    "id": "snap_3",
                    "review_recommendation": "approve_candidate",
                    "review_recommendation_reasons": ["guard_status:routing_candidate"],
                    "bulk_approval_recommendation": "eligible_for_bulk_approval",
                    "bulk_approval_recommendation_reasons": ["primary_intent:profile_memory_query"],
                },
            ],
            queue_path=Path(".runtime") / "queue.jsonl",
            example_limit=2,
        )

        self.assertIn("matched_items: total=3", text)
        self.assertIn("approve_candidate: total=2", text)
        self.assertIn("guard_status:routing_candidate=2", text)
        self.assertIn("example_ids: snap_1 snap_3", text)
        self.assertIn("bulk_approval_breakdown:", text)
        self.assertIn("eligible_for_bulk_approval: total=2", text)

    def test_cli_can_show_and_set_status(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"review-queue-manage-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            queue_path = temp_dir / "review-queue.jsonl"
            write_review_queue(
                [
                    {
                        "id": "snap_1",
                        "category": "snapshot_route",
                        "description": "route",
                        "raw_response_text": "{}",
                        "expected": {"valid": True},
                        "review_status": "pending_human_review",
                        "review_notes": "",
                        "review_recommendation": "approve_candidate",
                        "review_recommendation_reasons": ["guard_status:routing_candidate"],
                        "bulk_approval_recommendation": "eligible_for_bulk_approval",
                        "bulk_approval_recommendation_reasons": ["primary_intent:profile_memory_update"],
                    }
                ],
                queue_path,
            )

            show_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/manage_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "show",
                    "--id",
                    "snap_1",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            set_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/manage_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "set-status",
                    "--id",
                    "snap_1",
                    "--status",
                    "approved_for_baseline",
                    "--notes",
                    "manually reviewed",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            items = load_review_queue(queue_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, show_completed.returncode, show_completed.stderr)
        self.assertIn("id: snap_1", show_completed.stdout)
        self.assertIn("review_recommendation: approve_candidate", show_completed.stdout)
        self.assertIn("bulk_approval_recommendation: eligible_for_bulk_approval", show_completed.stdout)
        self.assertEqual(0, set_completed.returncode, set_completed.stderr)
        self.assertEqual("approved_for_baseline", find_review_queue_item(items, "snap_1")["review_status"])
        self.assertIn("manually reviewed", find_review_queue_item(items, "snap_1")["review_notes"])

    def test_cli_can_render_triage_report(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"review-queue-triage-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            queue_path = temp_dir / "review-queue.jsonl"
            write_review_queue(
                [
                    {
                        "id": "snap_1",
                        "category": "snapshot_route",
                        "description": "route",
                        "raw_response_text": "{}",
                        "expected": {"valid": True},
                        "review_status": "pending_human_review",
                        "review_notes": "",
                        "review_recommendation": "approve_candidate",
                        "review_recommendation_reasons": ["guard_status:routing_candidate"],
                        "bulk_approval_recommendation": "eligible_for_bulk_approval",
                        "bulk_approval_recommendation_reasons": ["primary_intent:profile_memory_update"],
                    },
                    {
                        "id": "snap_2",
                        "category": "snapshot_high_risk",
                        "description": "hold",
                        "raw_response_text": "{}",
                        "expected": {"valid": True},
                        "review_status": "pending_human_review",
                        "review_notes": "",
                        "review_recommendation": "manual_review_required",
                        "review_recommendation_reasons": ["blocked_reason:critical_risk:safety_or_urgent_signal"],
                        "bulk_approval_recommendation": "requires_manual_approval",
                        "bulk_approval_recommendation_reasons": ["primary_intent:health_alert"],
                    },
                ],
                queue_path,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/manage_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "triage-report",
                    "--review-status",
                    "pending_human_review",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("VitalAI second-layer review queue triage report: OK", completed.stdout)
        self.assertIn("approve_candidate: total=1", completed.stdout)
        self.assertIn("manual_review_required: total=1", completed.stdout)
        self.assertIn("eligible_for_bulk_approval: total=1", completed.stdout)

    def test_cli_can_list_and_bulk_set_status(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"review-queue-bulk-manage-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            queue_path = temp_dir / "review-queue.jsonl"
            write_review_queue(
                [
                    {
                        "id": "snap_1",
                        "category": "snapshot_route",
                        "description": "route",
                        "raw_response_text": "{}",
                        "expected": {"valid": True},
                        "review_status": "pending_human_review",
                        "review_notes": "",
                        "review_recommendation": "approve_candidate",
                        "bulk_approval_recommendation": "eligible_for_bulk_approval",
                        "suggested_validation": {"valid": True},
                        "suggested_guard": {"status": "routing_candidate"},
                        "parse_error": None,
                    },
                    {
                        "id": "snap_2",
                        "category": "snapshot_route",
                        "description": "invalid",
                        "raw_response_text": "{}",
                        "expected": {"valid": False},
                        "review_status": "pending_human_review",
                        "review_notes": "",
                        "review_recommendation": "baseline_negative_candidate",
                        "bulk_approval_recommendation": "not_applicable_for_bulk_approval",
                        "suggested_validation": {"valid": False},
                        "suggested_guard": {"status": "blocked"},
                        "parse_error": "bad json",
                    },
                ],
                queue_path,
            )

            list_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/manage_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "list",
                    "--bulk-approval",
                    "eligible_for_bulk_approval",
                    "--recommendation",
                    "approve_candidate",
                    "--validation",
                    "valid",
                    "--guard-status",
                    "routing_candidate",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            bulk_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/manage_second_layer_snapshot_review_queue.py",
                    "--queue",
                    str(queue_path),
                    "bulk-set-status",
                    "--bulk-approval",
                    "eligible_for_bulk_approval",
                    "--recommendation",
                    "approve_candidate",
                    "--validation",
                    "valid",
                    "--guard-status",
                    "routing_candidate",
                    "--status",
                    "approved_for_baseline",
                    "--notes",
                    "bulk reviewed",
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            items = load_review_queue(queue_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, list_completed.returncode, list_completed.stderr)
        self.assertIn("id=snap_1", list_completed.stdout)
        self.assertNotIn("id=snap_2", list_completed.stdout)
        self.assertEqual(0, bulk_completed.returncode, bulk_completed.stderr)
        self.assertEqual("approved_for_baseline", find_review_queue_item(items, "snap_1")["review_status"])
        self.assertEqual("pending_human_review", find_review_queue_item(items, "snap_2")["review_status"])
        self.assertIn("bulk reviewed", find_review_queue_item(items, "snap_1")["review_notes"])

    def test_format_review_queue_report_reports_counts(self) -> None:
        text = format_review_queue_report(
            {
                "total_items": 2,
                "status_counts": {"pending_human_review": 1, "approved_for_baseline": 1},
                "category_counts": {"snapshot_route": 2},
                "recommendation_counts": {"approve_candidate": 2},
                "bulk_approval_counts": {"eligible_for_bulk_approval": 2},
            },
            Path(".runtime") / "queue.jsonl",
        )

        self.assertIn("items: total=2", text)
        self.assertIn("approved_for_baseline=1", text)
        self.assertIn("snapshot_route=2", text)
        self.assertIn("approve_candidate=2", text)
        self.assertIn("eligible_for_bulk_approval=2", text)


if __name__ == "__main__":
    unittest.main()
