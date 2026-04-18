"""Tests for the offline second-layer hard-case evaluation script."""

from __future__ import annotations

import subprocess
import sys
import unittest

from scripts.intent_eval.evaluate_second_layer_hard_cases import (
    DEFAULT_DATASET_PATH,
    ROOT_DIR,
    evaluate_samples,
    format_text_report,
    load_samples,
)


class SecondLayerHardCaseEvalTests(unittest.TestCase):
    def test_dataset_loads_and_matches_expected_summary(self) -> None:
        summary = evaluate_samples(load_samples(DEFAULT_DATASET_PATH))

        self.assertEqual(22, summary["total_samples"])
        self.assertEqual(14, summary["valid_samples"])
        self.assertEqual(8, summary["invalid_samples"])
        self.assertEqual(0, summary["expectation_failure_count"])
        self.assertEqual(11, summary["routing_decision_counts"]["route_primary"])
        self.assertEqual(6, summary["routing_decision_counts"]["route_sequence"])
        self.assertEqual(3, summary["routing_decision_counts"]["ask_clarification"])
        self.assertEqual(1, summary["routing_decision_counts"]["reject"])
        self.assertEqual(1, summary["routing_decision_counts"]["hold_for_human_review"])
        self.assertEqual(2, summary["risk_flag_counts"]["health_signal:high"])
        self.assertEqual(1, summary["risk_flag_counts"]["health_signal:medium"])
        self.assertEqual(2, summary["risk_flag_counts"]["medication_signal:medium"])
        self.assertEqual(2, summary["guard_status_counts"]["clarification_candidate"])
        self.assertEqual(5, summary["guard_status_counts"]["routing_candidate"])
        self.assertEqual(5, summary["guard_status_counts"]["hold_for_human_review"])

    def test_text_report_is_human_readable(self) -> None:
        summary = evaluate_samples(load_samples(DEFAULT_DATASET_PATH))

        text = format_text_report(summary)

        self.assertIn("VitalAI second-layer hard-case eval: OK", text)
        self.assertIn("samples: total=22 valid=14 invalid=8", text)
        self.assertIn("routing_decisions: ask_clarification=3", text)
        self.assertIn("risk_flags: health_signal:high=2", text)
        self.assertIn("guard_statuses: clarification_candidate=2", text)

    def test_cli_text_output_runs_successfully(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/intent_eval/evaluate_second_layer_hard_cases.py",
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
        self.assertIn("VitalAI second-layer hard-case eval: OK", completed.stdout)
        self.assertIn("expectation_failures: 0", completed.stdout)


if __name__ == "__main__":
    unittest.main()
