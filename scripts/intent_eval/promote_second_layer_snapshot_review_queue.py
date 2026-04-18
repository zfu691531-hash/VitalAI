"""Promote approved second-layer review-queue items into a replay dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_QUEUE_PATH = ROOT_DIR / ".runtime" / "intent_eval" / "second_layer_snapshot_review_queue.jsonl"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "intent_eval" / "second_layer_response_snapshots.jsonl"
DEFAULT_APPROVED_STATUSES = ("approved_for_baseline",)


def load_review_queue(queue_path: Path) -> list[dict[str, Any]]:
    """Load review-queue items from JSONL."""
    items: list[dict[str, Any]] = []
    with queue_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} must be a JSON object.")
            items.append(payload)
    return items


def build_promoted_snapshot_dataset(
    queue_items: list[dict[str, Any]],
    *,
    existing_items: list[dict[str, Any]] | None = None,
    approved_statuses: tuple[str, ...] = DEFAULT_APPROVED_STATUSES,
) -> list[dict[str, Any]]:
    """Merge approved review-queue items into the replay dataset."""
    dataset_by_id: dict[str, dict[str, Any]] = {}
    for item in existing_items or []:
        item_id = str(item.get("id", "")).strip()
        if item_id:
            dataset_by_id[item_id] = dict(item)

    for queue_item in queue_items:
        review_status = str(queue_item.get("review_status", "")).strip()
        if review_status not in approved_statuses:
            continue
        promoted = _promote_queue_item(queue_item)
        dataset_by_id[promoted["id"]] = promoted

    return [dataset_by_id[item_id] for item_id in sorted(dataset_by_id)]


def write_snapshot_dataset(dataset: list[dict[str, Any]], output_path: Path) -> None:
    """Write the promoted replay dataset to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for item in dataset:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def format_promotion_summary(
    dataset: list[dict[str, Any]],
    output_path: Path,
    *,
    approved_count: int,
    skipped_count: int,
) -> str:
    """Render a compact promotion summary."""
    return "\n".join(
        [
            "VitalAI second-layer snapshot promotion: OK",
            f"output_path: {output_path}",
            f"dataset_items: {len(dataset)}",
            f"approved_promoted: {approved_count}",
            f"skipped_items: {skipped_count}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Promote approved review-queue items into the replay dataset."""
    parser = argparse.ArgumentParser(
        description="Promote approved second-layer review-queue items into the replay dataset.",
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=DEFAULT_QUEUE_PATH,
        help="Path to the review-queue JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSONL path for the replay dataset.",
    )
    parser.add_argument(
        "--approved-status",
        action="append",
        dest="approved_statuses",
        default=None,
        help="Review status that qualifies for promotion. Can be repeated.",
    )
    args = parser.parse_args(argv)

    approved_statuses = (
        tuple(args.approved_statuses)
        if args.approved_statuses
        else DEFAULT_APPROVED_STATUSES
    )
    queue_path = args.queue.resolve()
    queue_items = load_review_queue(queue_path)
    output_path = args.output.resolve()
    existing_items = load_review_queue(output_path) if output_path.exists() else []
    dataset = build_promoted_snapshot_dataset(
        queue_items,
        existing_items=existing_items,
        approved_statuses=approved_statuses,
    )
    write_snapshot_dataset(dataset, output_path)
    approved_count = sum(
        1 for item in queue_items if str(item.get("review_status", "")).strip() in approved_statuses
    )
    skipped_count = len(queue_items) - approved_count
    print(
        format_promotion_summary(
            dataset,
            output_path,
            approved_count=approved_count,
            skipped_count=skipped_count,
        )
    )
    return 0


def _promote_queue_item(queue_item: dict[str, Any]) -> dict[str, Any]:
    item_id = str(queue_item.get("id", "")).strip()
    if not item_id:
        raise ValueError("Approved review-queue item is missing id.")
    return {
        "id": item_id,
        "category": str(queue_item.get("category", "uncategorized")),
        "description": str(queue_item.get("description", "")),
        "raw_response_text": str(queue_item.get("raw_response_text", "")),
        "expected": dict(queue_item.get("expected", {})),
        "review_metadata": {
            "review_status": queue_item.get("review_status"),
            "review_notes": queue_item.get("review_notes", ""),
            "review_recommendation": queue_item.get("review_recommendation"),
            "review_recommendation_reasons": list(queue_item.get("review_recommendation_reasons") or []),
            "bulk_approval_recommendation": queue_item.get("bulk_approval_recommendation"),
            "bulk_approval_recommendation_reasons": list(
                queue_item.get("bulk_approval_recommendation_reasons") or []
            ),
            "source_capture": dict(queue_item.get("source_capture") or {}),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
