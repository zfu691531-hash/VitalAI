"""Build a human-review queue from captured second-layer response snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.intent_eval.review_policy import (
    suggest_bulk_approval_recommendation,
    suggest_review_recommendation,
)

DEFAULT_CAPTURE_PATH = ROOT_DIR / ".runtime" / "intent_eval" / "second_layer_captured_snapshots.jsonl"
DEFAULT_QUEUE_PATH = ROOT_DIR / ".runtime" / "intent_eval" / "second_layer_snapshot_review_queue.jsonl"


def load_capture_records(capture_path: Path) -> list[dict[str, Any]]:
    """Load captured response records from JSONL."""
    records: list[dict[str, Any]] = []
    with capture_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} must be a JSON object.")
            records.append(payload)
    return records


def build_review_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform captured snapshots into evaluator-compatible review items."""
    queue: list[dict[str, Any]] = []
    for record in records:
        recommendation, recommendation_reasons = suggest_review_recommendation(record)
        bulk_approval_recommendation, bulk_approval_reasons = suggest_bulk_approval_recommendation(
            record,
            review_recommendation=recommendation,
        )
        queue.append(
            {
                "id": str(record["id"]),
                "category": str(record.get("category", "uncategorized")),
                "description": str(record.get("description", "")),
                "raw_response_text": str(record.get("raw_response_text", "")),
                "expected": _suggest_expected(record),
                "review_status": "pending_human_review",
                "review_notes": "",
                "review_recommendation": recommendation,
                "review_recommendation_reasons": recommendation_reasons,
                "bulk_approval_recommendation": bulk_approval_recommendation,
                "bulk_approval_recommendation_reasons": bulk_approval_reasons,
                "source_capture": {
                    "captured_at": record.get("captured_at"),
                    "model": record.get("request", {}).get("model"),
                    "base_url": record.get("request", {}).get("base_url"),
                    "trace_id": record.get("request", {}).get("trace_id"),
                },
                "suggested_validation": record.get("validation"),
                "suggested_guard": record.get("guard"),
                "parse_error": record.get("parse_error"),
                "request_error": record.get("request_error"),
            }
        )
    return queue


def write_review_queue(queue: list[dict[str, Any]], output_path: Path) -> None:
    """Write the review queue to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in queue:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def format_review_queue_summary(queue: list[dict[str, Any]], output_path: Path) -> str:
    """Render a compact review-queue summary."""
    parse_failures = sum(1 for item in queue if item.get("parse_error"))
    valid = sum(
        1
        for item in queue
        if bool((item.get("suggested_validation") or {}).get("valid"))
    )
    recommendation_counts: dict[str, int] = {}
    bulk_approval_counts: dict[str, int] = {}
    for item in queue:
        recommendation = str(item.get("review_recommendation", "unknown")).strip() or "unknown"
        bulk_approval_recommendation = (
            str(item.get("bulk_approval_recommendation", "unknown")).strip() or "unknown"
        )
        recommendation_counts[recommendation] = recommendation_counts.get(recommendation, 0) + 1
        bulk_approval_counts[bulk_approval_recommendation] = (
            bulk_approval_counts.get(bulk_approval_recommendation, 0) + 1
        )
    return "\n".join(
        [
            "VitalAI second-layer snapshot review queue: OK",
            f"output_path: {output_path}",
            f"items: total={len(queue)} valid={valid} invalid={len(queue) - valid}",
            f"parse_failures: {parse_failures}",
            "recommendations: " + _format_counts(recommendation_counts),
            "bulk_approval: " + _format_counts(bulk_approval_counts),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Build one review queue from captured snapshots."""
    parser = argparse.ArgumentParser(
        description="Build a human-review queue from captured second-layer response snapshots.",
    )
    parser.add_argument(
        "--capture",
        type=Path,
        default=DEFAULT_CAPTURE_PATH,
        help="Path to the captured snapshot JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_QUEUE_PATH,
        help="Output JSONL path for the review queue.",
    )
    args = parser.parse_args(argv)

    capture_path = args.capture.resolve()
    queue = build_review_queue(load_capture_records(capture_path))
    output_path = args.output.resolve()
    write_review_queue(queue, output_path)
    print(format_review_queue_summary(queue, output_path))
    return 0


def _suggest_expected(record: dict[str, Any]) -> dict[str, Any]:
    parse_error = record.get("parse_error")
    if isinstance(parse_error, str) and parse_error.strip():
        return {
            "valid": False,
            "parse_error_contains": parse_error.strip(),
        }

    validation = record.get("validation")
    if isinstance(validation, dict) and validation.get("valid") is True:
        guard = record.get("guard") or {}
        blocked_reasons = guard.get("blocked_reasons", [])
        return {
            "valid": True,
            "guard_status": guard.get("status"),
            "blocked_reasons": list(blocked_reasons) if isinstance(blocked_reasons, list) else [],
        }

    issues = []
    if isinstance(validation, dict):
        for issue in validation.get("issues", []):
            if isinstance(issue, dict):
                code = issue.get("code")
                if isinstance(code, str) and code:
                    issues.append(code)
    return {
        "valid": False,
        "issue_codes": issues,
    }
def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "<none>"
    return " ".join(f"{key}={value}" for key, value in sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
