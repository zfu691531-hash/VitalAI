"""Tests for building a review queue from captured second-layer snapshots."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from uuid import uuid4

from scripts.intent_eval.build_second_layer_snapshot_review_queue import (
    ROOT_DIR,
    build_review_queue,
    format_review_queue_summary,
    load_capture_records,
    write_review_queue,
)
from scripts.intent_eval.evaluate_second_layer_hard_cases import evaluate_samples, load_samples


class BuildSecondLayerSnapshotReviewQueueTests(unittest.TestCase):
    def test_build_review_queue_suggests_expected_values(self) -> None:
        records = [
            {
                "id": "capture_1",
                "category": "mental_care+medication",
                "description": "clarification",
                "raw_response_text": "{}",
                "parse_error": None,
                "validation": {"valid": True},
                "guard": {"status": "clarification_candidate", "blocked_reasons": []},
                "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
            },
            {
                "id": "capture_2",
                "category": "snapshot_parse_failure",
                "raw_response_text": "not json",
                "parse_error": "LLM response did not contain a valid JSON object.",
                "validation": None,
                "guard": None,
                "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
            },
            {
                "id": "capture_3",
                "category": "snapshot_invalid_schema",
                "raw_response_text": "{\"status\":\"needs_clarification\"}",
                "parse_error": None,
                "validation": {"valid": False, "issues": [{"code": "required_for_clarification"}]},
                "guard": None,
                "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
            },
        ]

        queue = build_review_queue(records)

        self.assertEqual(3, len(queue))
        self.assertEqual("pending_human_review", queue[0]["review_status"])
        self.assertEqual("clarification_candidate", queue[0]["expected"]["guard_status"])
        self.assertEqual("approve_candidate", queue[0]["review_recommendation"])
        self.assertEqual("eligible_for_bulk_approval", queue[0]["bulk_approval_recommendation"])
        self.assertIn("valid JSON object", queue[1]["expected"]["parse_error_contains"])
        self.assertEqual("baseline_negative_candidate", queue[1]["review_recommendation"])
        self.assertEqual("not_applicable_for_bulk_approval", queue[1]["bulk_approval_recommendation"])
        self.assertEqual(["required_for_clarification"], queue[2]["expected"]["issue_codes"])
        self.assertEqual("baseline_negative_candidate", queue[2]["review_recommendation"])
        self.assertEqual("not_applicable_for_bulk_approval", queue[2]["bulk_approval_recommendation"])

    def test_build_review_queue_marks_hold_cases_as_manual_review_required(self) -> None:
        queue = build_review_queue(
            [
                {
                    "id": "capture_hold",
                    "category": "snapshot_high_risk",
                    "description": "hold",
                    "raw_response_text": "{}",
                    "parse_error": None,
                    "validation": {"valid": True},
                    "guard": {
                        "status": "hold_for_human_review",
                        "blocked_reasons": ["critical_risk:safety_or_urgent_signal"],
                    },
                    "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
                }
            ]
        )

        self.assertEqual("manual_review_required", queue[0]["review_recommendation"])
        self.assertEqual("not_applicable_for_bulk_approval", queue[0]["bulk_approval_recommendation"])
        self.assertIn(
            "blocked_reason:critical_risk:safety_or_urgent_signal",
            queue[0]["review_recommendation_reasons"],
        )

    def test_build_review_queue_marks_risky_clarification_as_manual_bulk_review(self) -> None:
        queue = build_review_queue(
            [
                {
                    "id": "capture_risky_clarification",
                    "category": "health+daily_life",
                    "description": "clarification with health risk",
                    "raw_response_text": "{}",
                    "parse_error": None,
                    "validation": {
                        "valid": True,
                        "result": {
                            "risk_flags": [
                                {
                                    "kind": "dizziness",
                                    "severity": "medium",
                                    "reason": "reported dizziness",
                                }
                            ],
                        },
                    },
                    "guard": {
                        "status": "clarification_candidate",
                        "blocked_reasons": [],
                    },
                    "request": {"model": "qwen3-max", "base_url": "https://example.invalid"},
                }
            ]
        )

        self.assertEqual("approve_candidate", queue[0]["review_recommendation"])
        self.assertEqual("requires_manual_approval", queue[0]["bulk_approval_recommendation"])
        self.assertIn("guard_status:clarification_candidate", queue[0]["bulk_approval_recommendation_reasons"])
        self.assertIn("risk_flag:dizziness", queue[0]["bulk_approval_recommendation_reasons"])

    def test_build_review_queue_marks_safe_routing_candidate_as_bulk_eligible(self) -> None:
        queue = build_review_queue(
            [
                {
                    "id": "capture_safe_route",
                    "category": "snapshot_route",
                    "description": "safe route",
                    "raw_response_text": "{}",
                    "parse_error": None,
                    "validation": {
                        "valid": True,
                        "result": {
                            "risk_flags": [],
                        },
                    },
                    "guard": {
                        "status": "routing_candidate",
                        "routing_candidate": {
                            "intent": "profile_memory_update",
                            "routing_decision": "route_primary",
                            "confidence": 0.91,
                            "secondary_intents": [],
                        },
                    },
                    "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
                }
            ]
        )

        self.assertEqual("approve_candidate", queue[0]["review_recommendation"])
        self.assertEqual("eligible_for_bulk_approval", queue[0]["bulk_approval_recommendation"])

    def test_build_review_queue_marks_health_route_as_manual_bulk_review(self) -> None:
        queue = build_review_queue(
            [
                {
                    "id": "capture_health_route",
                    "category": "snapshot_route",
                    "description": "health route",
                    "raw_response_text": "{}",
                    "parse_error": None,
                    "validation": {
                        "valid": True,
                        "result": {
                            "risk_flags": [],
                        },
                    },
                    "guard": {
                        "status": "routing_candidate",
                        "routing_candidate": {
                            "intent": "health_alert",
                            "routing_decision": "route_primary",
                            "confidence": 0.97,
                            "secondary_intents": [],
                        },
                    },
                    "request": {"model": "glm-5.1", "base_url": "https://example.invalid"},
                }
            ]
        )

        self.assertEqual("approve_candidate", queue[0]["review_recommendation"])
        self.assertEqual("requires_manual_approval", queue[0]["bulk_approval_recommendation"])
        self.assertIn("primary_intent:health_alert", queue[0]["bulk_approval_recommendation_reasons"])

    def test_review_queue_can_be_evaluated_by_existing_eval_script(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"snapshot-review-queue-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            queue_path = temp_dir / "review-queue.jsonl"
            write_review_queue(
                [
                    {
                        "id": "capture_1",
                        "category": "snapshot_route",
                        "description": "route",
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
                        "review_status": "pending_human_review",
                        "review_notes": "",
                    }
                ],
                queue_path,
            )

            summary = evaluate_samples(load_samples(queue_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(1, summary["total_samples"])
        self.assertEqual(0, summary["expectation_failure_count"])

    def test_cli_builds_review_queue_file(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"snapshot-review-queue-cli-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            capture_path = temp_dir / "captured.jsonl"
            capture_path.write_text(
                (
                    "{\"id\":\"capture_1\",\"category\":\"snapshot_parse_failure\","
                    "\"raw_response_text\":\"not json\","
                    "\"parse_error\":\"LLM response did not contain a valid JSON object.\","
                    "\"validation\":null,\"guard\":null,\"request\":{\"model\":\"glm-5.1\"}}\n"
                ),
                encoding="utf-8",
            )
            output_path = temp_dir / "review-queue.jsonl"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/intent_eval/build_second_layer_snapshot_review_queue.py",
                    "--capture",
                    str(capture_path),
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
            written = output_path.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("VitalAI second-layer snapshot review queue: OK", completed.stdout)
        self.assertIn("pending_human_review", written)

    def test_format_review_queue_summary_reports_counts(self) -> None:
        text = format_review_queue_summary(
            [
                {"parse_error": None, "suggested_validation": {"valid": True}},
                {"parse_error": "boom", "suggested_validation": {"valid": False}},
            ],
            Path(".runtime") / "review-queue.jsonl",
        )

        self.assertIn("items: total=2 valid=1 invalid=1", text)
        self.assertIn("parse_failures: 1", text)
        self.assertIn("recommendations:", text)
        self.assertIn("bulk_approval:", text)


if __name__ == "__main__":
    unittest.main()
