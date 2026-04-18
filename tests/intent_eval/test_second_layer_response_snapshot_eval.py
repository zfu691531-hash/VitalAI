"""Tests for replaying second-layer raw response snapshots offline."""

from __future__ import annotations

import subprocess
import sys
import unittest

from scripts.intent_eval.evaluate_second_layer_hard_cases import (
    ROOT_DIR,
    evaluate_samples,
    format_text_report,
    load_samples,
)


SNAPSHOT_DATASET_PATH = ROOT_DIR / "data" / "intent_eval" / "second_layer_response_snapshots.jsonl"


class SecondLayerResponseSnapshotEvalTests(unittest.TestCase):
    def test_snapshot_dataset_replays_successfully(self) -> None:
        summary = evaluate_samples(load_samples(SNAPSHOT_DATASET_PATH))

        self.assertGreaterEqual(summary["total_samples"], 5)
        self.assertEqual(
            {"raw_response_text": summary["total_samples"]},
            summary["input_kind_counts"],
        )
        self.assertEqual(
            summary["total_samples"],
            summary["valid_samples"] + summary["invalid_samples"],
        )
        self.assertGreaterEqual(summary["valid_samples"], 3)
        self.assertGreaterEqual(summary["invalid_samples"], 2)
        self.assertGreaterEqual(summary["parse_failure_count"], 1)
        self.assertEqual(0, summary["expectation_failure_count"])
        self.assertGreaterEqual(summary["routing_decision_counts"]["<parse_failed>"], 1)
        self.assertGreaterEqual(summary["guard_status_counts"]["clarification_candidate"], 1)
        self.assertGreaterEqual(summary["guard_status_counts"]["routing_candidate"], 1)
        self.assertGreaterEqual(summary["guard_status_counts"]["hold_for_human_review"], 1)

    def test_snapshot_text_report_is_human_readable(self) -> None:
        summary = evaluate_samples(load_samples(SNAPSHOT_DATASET_PATH))

        text = format_text_report(summary)

        self.assertIn("VitalAI second-layer hard-case eval: OK", text)
        self.assertIn("input_kinds: raw_response_text=", text)
        self.assertIn("parse_failures:", text)
        self.assertIn("routing_decisions: <parse_failed>=1", text)

    def test_snapshot_cli_text_output_runs_successfully(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/intent_eval/evaluate_second_layer_hard_cases.py",
                "--dataset",
                str(SNAPSHOT_DATASET_PATH),
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

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("input_kinds: raw_response_text=", completed.stdout)
        self.assertIn("parse_failures:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
