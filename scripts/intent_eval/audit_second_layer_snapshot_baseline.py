"""Audit the promoted second-layer snapshot baseline dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_DATASET_PATH = ROOT_DIR / "data" / "intent_eval" / "second_layer_response_snapshots.jsonl"


def load_snapshot_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    """Load promoted snapshot baseline items from JSONL."""
    items: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} must be a JSON object.")
            items.append(payload)
    return items


def audit_snapshot_dataset(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build provenance and quality summary for the promoted baseline dataset."""
    category_counts: dict[str, int] = {}
    expected_valid_counts: dict[str, int] = {}
    expected_guard_counts: dict[str, int] = {}
    review_status_counts: dict[str, int] = {}
    review_recommendation_counts: dict[str, int] = {}
    bulk_approval_counts: dict[str, int] = {}
    duplicate_ids: list[str] = []
    missing_review_metadata_ids: list[str] = []
    missing_source_capture_ids: list[str] = []

    seen_ids: set[str] = set()
    for item in items:
        item_id = str(item.get("id", "")).strip()
        if item_id in seen_ids and item_id:
            duplicate_ids.append(item_id)
        if item_id:
            seen_ids.add(item_id)

        category = str(item.get("category", "uncategorized")).strip() or "uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1

        expected = item.get("expected") or {}
        expected_valid = bool(expected.get("valid"))
        expected_valid_key = "valid" if expected_valid else "invalid"
        expected_valid_counts[expected_valid_key] = expected_valid_counts.get(expected_valid_key, 0) + 1
        guard_status = str(expected.get("guard_status", "<none>")).strip() or "<none>"
        expected_guard_counts[guard_status] = expected_guard_counts.get(guard_status, 0) + 1

        review_metadata = item.get("review_metadata")
        if not isinstance(review_metadata, dict):
            if item_id:
                missing_review_metadata_ids.append(item_id)
            continue
        review_status = str(review_metadata.get("review_status", "unknown")).strip() or "unknown"
        review_recommendation = str(review_metadata.get("review_recommendation", "unknown")).strip() or "unknown"
        bulk_approval = (
            str(review_metadata.get("bulk_approval_recommendation", "unknown")).strip() or "unknown"
        )
        review_status_counts[review_status] = review_status_counts.get(review_status, 0) + 1
        review_recommendation_counts[review_recommendation] = (
            review_recommendation_counts.get(review_recommendation, 0) + 1
        )
        bulk_approval_counts[bulk_approval] = bulk_approval_counts.get(bulk_approval, 0) + 1

        source_capture = review_metadata.get("source_capture")
        if not isinstance(source_capture, dict) or not source_capture:
            if item_id:
                missing_source_capture_ids.append(item_id)

    return {
        "total_items": len(items),
        "category_counts": dict(sorted(category_counts.items())),
        "expected_valid_counts": dict(sorted(expected_valid_counts.items())),
        "expected_guard_counts": dict(sorted(expected_guard_counts.items())),
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "review_recommendation_counts": dict(sorted(review_recommendation_counts.items())),
        "bulk_approval_counts": dict(sorted(bulk_approval_counts.items())),
        "duplicate_ids": sorted(duplicate_ids),
        "missing_review_metadata_ids": sorted(missing_review_metadata_ids),
        "missing_source_capture_ids": sorted(missing_source_capture_ids),
    }


def format_audit_report(summary: dict[str, Any], dataset_path: Path) -> str:
    """Render a human-readable audit report."""
    return "\n".join(
        [
            "VitalAI second-layer snapshot baseline audit: OK",
            f"dataset_path: {dataset_path}",
            f"items: total={summary['total_items']}",
            "categories: " + _format_counts(summary["category_counts"]),
            "expected_valid: " + _format_counts(summary["expected_valid_counts"]),
            "expected_guard: " + _format_counts(summary["expected_guard_counts"]),
            "review_statuses: " + _format_counts(summary["review_status_counts"]),
            "review_recommendations: " + _format_counts(summary["review_recommendation_counts"]),
            "bulk_approval: " + _format_counts(summary["bulk_approval_counts"]),
            "duplicate_ids: " + _format_id_list(summary["duplicate_ids"]),
            "missing_review_metadata_ids: " + _format_id_list(summary["missing_review_metadata_ids"]),
            "missing_source_capture_ids: " + _format_id_list(summary["missing_source_capture_ids"]),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Audit one promoted second-layer snapshot dataset."""
    parser = argparse.ArgumentParser(
        description="Audit the promoted second-layer snapshot baseline dataset.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the promoted snapshot baseline JSONL file.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    dataset_path = args.dataset.resolve()
    summary = audit_snapshot_dataset(load_snapshot_dataset(dataset_path))
    if args.output == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_audit_report(summary, dataset_path))
    return 0


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "<none>"
    return " ".join(f"{key}={value}" for key, value in counts.items())


def _format_id_list(values: list[str]) -> str:
    if not values:
        return "<none>"
    return " ".join(values)


if __name__ == "__main__":
    raise SystemExit(main())
