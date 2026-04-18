"""Manage second-layer snapshot review-queue items."""

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


def write_review_queue(items: list[dict[str, Any]], queue_path: Path) -> None:
    """Write review-queue items back to JSONL."""
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def summarize_review_queue(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate counts for the review queue."""
    status_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    recommendation_counts: dict[str, int] = {}
    bulk_approval_counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("review_status", "unknown")).strip() or "unknown"
        category = str(item.get("category", "uncategorized")).strip() or "uncategorized"
        recommendation = str(item.get("review_recommendation", "unknown")).strip() or "unknown"
        bulk_approval_recommendation = (
            str(item.get("bulk_approval_recommendation", "unknown")).strip() or "unknown"
        )
        status_counts[status] = status_counts.get(status, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        recommendation_counts[recommendation] = recommendation_counts.get(recommendation, 0) + 1
        bulk_approval_counts[bulk_approval_recommendation] = (
            bulk_approval_counts.get(bulk_approval_recommendation, 0) + 1
        )
    return {
        "total_items": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "recommendation_counts": dict(sorted(recommendation_counts.items())),
        "bulk_approval_counts": dict(sorted(bulk_approval_counts.items())),
    }


def filter_review_queue_items(
    items: list[dict[str, Any]],
    *,
    review_statuses: list[str] | None = None,
    categories: list[str] | None = None,
    guard_statuses: list[str] | None = None,
    recommendations: list[str] | None = None,
    bulk_approval_recommendations: list[str] | None = None,
    validation_state: str = "any",
    parse_error_state: str = "any",
) -> list[dict[str, Any]]:
    """Filter queue items for review and batch operations."""
    normalized_statuses = {value.strip() for value in review_statuses or [] if value.strip()}
    normalized_categories = {value.strip() for value in categories or [] if value.strip()}
    normalized_guard_statuses = {value.strip() for value in guard_statuses or [] if value.strip()}
    normalized_recommendations = {value.strip() for value in recommendations or [] if value.strip()}
    normalized_bulk_approval_recommendations = {
        value.strip() for value in bulk_approval_recommendations or [] if value.strip()
    }
    normalized_validation = validation_state.strip().lower()
    normalized_parse_error = parse_error_state.strip().lower()
    filtered: list[dict[str, Any]] = []
    for item in items:
        if normalized_statuses and str(item.get("review_status", "")).strip() not in normalized_statuses:
            continue
        if normalized_categories and str(item.get("category", "")).strip() not in normalized_categories:
            continue
        if normalized_recommendations and str(item.get("review_recommendation", "")).strip() not in normalized_recommendations:
            continue
        if (
            normalized_bulk_approval_recommendations
            and str(item.get("bulk_approval_recommendation", "")).strip()
            not in normalized_bulk_approval_recommendations
        ):
            continue
        if normalized_guard_statuses:
            guard_status = str((item.get("suggested_guard") or {}).get("status", "")).strip()
            if guard_status not in normalized_guard_statuses:
                continue
        validation = bool((item.get("suggested_validation") or {}).get("valid"))
        if normalized_validation == "valid" and not validation:
            continue
        if normalized_validation == "invalid" and validation:
            continue
        parse_error = item.get("parse_error")
        has_parse_error = isinstance(parse_error, str) and bool(parse_error.strip())
        if normalized_parse_error == "yes" and not has_parse_error:
            continue
        if normalized_parse_error == "no" and has_parse_error:
            continue
        filtered.append(item)
    return filtered


def format_review_queue_report(summary: dict[str, Any], queue_path: Path) -> str:
    """Render a compact queue summary."""
    return "\n".join(
        [
            "VitalAI second-layer review queue manager: OK",
            f"queue_path: {queue_path}",
            f"items: total={summary['total_items']}",
            "statuses: " + _format_counts(summary["status_counts"]),
            "categories: " + _format_counts(summary["category_counts"]),
            "recommendations: " + _format_counts(summary["recommendation_counts"]),
            "bulk_approval: " + _format_counts(summary["bulk_approval_counts"]),
        ]
    )


def find_review_queue_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    """Find one queue item by id."""
    normalized = item_id.strip()
    for item in items:
        if str(item.get("id", "")).strip() == normalized:
            return item
    return None


def format_review_queue_item(item: dict[str, Any], *, include_raw_response: bool = False) -> str:
    """Render one queue item for human review."""
    lines = [
        f"id: {item.get('id', '')}",
        f"category: {item.get('category', '')}",
        f"review_status: {item.get('review_status', '')}",
        f"review_recommendation: {item.get('review_recommendation', '')}",
        f"bulk_approval_recommendation: {item.get('bulk_approval_recommendation', '')}",
        f"description: {item.get('description', '')}",
        f"review_notes: {item.get('review_notes', '')}",
        "expected: " + json.dumps(item.get("expected", {}), ensure_ascii=False),
    ]
    recommendation_reasons = item.get("review_recommendation_reasons") or []
    if recommendation_reasons:
        lines.append("review_recommendation_reasons: " + ", ".join(str(reason) for reason in recommendation_reasons))
    bulk_approval_reasons = item.get("bulk_approval_recommendation_reasons") or []
    if bulk_approval_reasons:
        lines.append("bulk_approval_recommendation_reasons: " + ", ".join(str(reason) for reason in bulk_approval_reasons))
    if include_raw_response:
        lines.append("raw_response_text:")
        lines.append(str(item.get("raw_response_text", "")))
    return "\n".join(lines)


def format_review_queue_list(
    items: list[dict[str, Any]],
    *,
    queue_path: Path,
    limit: int | None = None,
) -> str:
    """Render a compact filtered item list."""
    if limit is not None and limit >= 0:
        visible_items = items[:limit]
    else:
        visible_items = list(items)
    lines = [
        "VitalAI second-layer review queue list: OK",
        f"queue_path: {queue_path}",
        f"matched_items: total={len(items)} shown={len(visible_items)}",
    ]
    for item in visible_items:
        validation = "valid" if bool((item.get("suggested_validation") or {}).get("valid")) else "invalid"
        guard_status = str((item.get("suggested_guard") or {}).get("status", "")).strip() or "<none>"
        parse_error = item.get("parse_error")
        parse_error_state = "yes" if isinstance(parse_error, str) and parse_error.strip() else "no"
        recommendation = str(item.get("review_recommendation", "")).strip() or "<none>"
        bulk_approval_recommendation = str(item.get("bulk_approval_recommendation", "")).strip() or "<none>"
        lines.append(
            " | ".join(
                [
                    f"id={item.get('id', '')}",
                    f"review_status={item.get('review_status', '')}",
                    f"recommendation={recommendation}",
                    f"bulk_approval={bulk_approval_recommendation}",
                    f"category={item.get('category', '')}",
                    f"validation={validation}",
                    f"guard={guard_status}",
                    f"parse_error={parse_error_state}",
                ]
            )
        )
    return "\n".join(lines)


def format_review_queue_triage_report(
    items: list[dict[str, Any]],
    *,
    queue_path: Path,
    example_limit: int = 3,
) -> str:
    """Render a grouped triage report for the current queue subset."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        recommendation = str(item.get("review_recommendation", "unknown")).strip() or "unknown"
        grouped.setdefault(recommendation, []).append(item)
    bulk_grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        bulk_recommendation = str(item.get("bulk_approval_recommendation", "unknown")).strip() or "unknown"
        bulk_grouped.setdefault(bulk_recommendation, []).append(item)

    lines = [
        "VitalAI second-layer review queue triage report: OK",
        f"queue_path: {queue_path}",
        f"matched_items: total={len(items)}",
    ]
    for recommendation in sorted(grouped):
        recommendation_items = grouped[recommendation]
        reason_counts: dict[str, int] = {}
        for item in recommendation_items:
            for reason in item.get("review_recommendation_reasons") or []:
                normalized_reason = str(reason).strip()
                if not normalized_reason:
                    continue
                reason_counts[normalized_reason] = reason_counts.get(normalized_reason, 0) + 1
        example_ids = [
            str(item.get("id", "")).strip()
            for item in recommendation_items[: max(example_limit, 0)]
            if str(item.get("id", "")).strip()
        ]
        lines.append(f"{recommendation}: total={len(recommendation_items)}")
        lines.append("reason_counts: " + _format_counts(reason_counts))
        lines.append("example_ids: " + (" ".join(example_ids) if example_ids else "<none>"))
    lines.append("bulk_approval_breakdown:")
    for recommendation in sorted(bulk_grouped):
        recommendation_items = bulk_grouped[recommendation]
        reason_counts: dict[str, int] = {}
        for item in recommendation_items:
            for reason in item.get("bulk_approval_recommendation_reasons") or []:
                normalized_reason = str(reason).strip()
                if not normalized_reason:
                    continue
                reason_counts[normalized_reason] = reason_counts.get(normalized_reason, 0) + 1
        example_ids = [
            str(item.get("id", "")).strip()
            for item in recommendation_items[: max(example_limit, 0)]
            if str(item.get("id", "")).strip()
        ]
        lines.append(f"{recommendation}: total={len(recommendation_items)}")
        lines.append("reason_counts: " + _format_counts(reason_counts))
        lines.append("example_ids: " + (" ".join(example_ids) if example_ids else "<none>"))
    return "\n".join(lines)


def update_review_queue_items(
    items: list[dict[str, Any]],
    *,
    item_ids: list[str],
    review_status: str,
    review_notes: str | None = None,
    append_notes: bool = False,
) -> list[dict[str, Any]]:
    """Update review status and optional notes for one or more queue items."""
    normalized_ids = [item_id.strip() for item_id in item_ids if item_id.strip()]
    missing_ids = [item_id for item_id in normalized_ids if find_review_queue_item(items, item_id) is None]
    if missing_ids:
        raise ValueError(f"Review queue items not found: {', '.join(missing_ids)}")

    for item in items:
        if str(item.get("id", "")).strip() not in normalized_ids:
            continue
        item["review_status"] = review_status.strip()
        if review_notes is None:
            continue
        existing_notes = str(item.get("review_notes", "")).strip()
        if append_notes and existing_notes and review_notes.strip():
            item["review_notes"] = existing_notes + "\n" + review_notes.strip()
        else:
            item["review_notes"] = review_notes.strip()
    return items


def build_filter_kwargs_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Normalize CLI filter arguments into filter_review_queue_items kwargs."""
    return {
        "review_statuses": list(getattr(args, "review_statuses", []) or []),
        "categories": list(getattr(args, "categories", []) or []),
        "guard_statuses": list(getattr(args, "guard_statuses", []) or []),
        "recommendations": list(getattr(args, "recommendations", []) or []),
        "bulk_approval_recommendations": list(getattr(args, "bulk_approval_recommendations", []) or []),
        "validation_state": str(getattr(args, "validation_state", "any") or "any"),
        "parse_error_state": str(getattr(args, "parse_error_state", "any") or "any"),
    }


def main(argv: list[str] | None = None) -> int:
    """Manage the review queue."""
    parser = argparse.ArgumentParser(
        description="Manage second-layer snapshot review-queue items.",
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=DEFAULT_QUEUE_PATH,
        help="Path to the review-queue JSONL file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Show queue summary counts.")

    list_parser = subparsers.add_parser("list", help="List queue items with optional filters.")
    _add_filter_arguments(list_parser)
    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of matched items to print. Use -1 to show all.",
    )

    triage_report_parser = subparsers.add_parser(
        "triage-report",
        help="Show grouped recommendation buckets and top reasons for the current queue subset.",
    )
    _add_filter_arguments(triage_report_parser)
    triage_report_parser.add_argument(
        "--example-limit",
        type=int,
        default=3,
        help="Maximum example ids to show per recommendation bucket.",
    )

    show_parser = subparsers.add_parser("show", help="Show one queue item.")
    show_parser.add_argument("--id", required=True, help="Queue item id.")
    show_parser.add_argument(
        "--include-raw-response",
        action="store_true",
        help="Include raw_response_text in the output.",
    )

    set_status_parser = subparsers.add_parser("set-status", help="Update review status for one or more items.")
    set_status_parser.add_argument("--id", action="append", required=True, dest="item_ids", help="Queue item id.")
    set_status_parser.add_argument("--status", required=True, help="New review status.")
    set_status_parser.add_argument("--notes", default=None, help="Optional review notes.")
    set_status_parser.add_argument(
        "--append-notes",
        action="store_true",
        help="Append notes instead of replacing existing notes.",
    )

    bulk_set_status_parser = subparsers.add_parser(
        "bulk-set-status",
        help="Update review status for all queue items matching the provided filters.",
    )
    _add_filter_arguments(bulk_set_status_parser)
    bulk_set_status_parser.add_argument("--status", required=True, help="New review status.")
    bulk_set_status_parser.add_argument("--notes", default=None, help="Optional review notes.")
    bulk_set_status_parser.add_argument(
        "--append-notes",
        action="store_true",
        help="Append notes instead of replacing existing notes.",
    )
    bulk_set_status_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matched items without writing changes.",
    )

    args = parser.parse_args(argv)
    queue_path = args.queue.resolve()
    items = load_review_queue(queue_path)

    if args.command == "summary":
        print(format_review_queue_report(summarize_review_queue(items), queue_path))
        return 0

    if args.command == "list":
        filtered_items = filter_review_queue_items(items, **build_filter_kwargs_from_args(args))
        print(format_review_queue_list(filtered_items, queue_path=queue_path, limit=args.limit))
        return 0

    if args.command == "triage-report":
        filtered_items = filter_review_queue_items(items, **build_filter_kwargs_from_args(args))
        print(
            format_review_queue_triage_report(
                filtered_items,
                queue_path=queue_path,
                example_limit=args.example_limit,
            )
        )
        return 0

    if args.command == "show":
        item = find_review_queue_item(items, args.id)
        if item is None:
            raise ValueError(f"Review queue item not found: {args.id}")
        print(format_review_queue_item(item, include_raw_response=args.include_raw_response))
        return 0

    if args.command == "set-status":
        update_review_queue_items(
            items,
            item_ids=list(args.item_ids),
            review_status=args.status,
            review_notes=args.notes,
            append_notes=args.append_notes,
        )
        write_review_queue(items, queue_path)
        print(format_review_queue_report(summarize_review_queue(items), queue_path))
        return 0

    if args.command == "bulk-set-status":
        filtered_items = filter_review_queue_items(items, **build_filter_kwargs_from_args(args))
        if not filtered_items:
            raise ValueError("No review queue items matched the provided filters.")
        print(format_review_queue_list(filtered_items, queue_path=queue_path, limit=-1))
        if args.dry_run:
            return 0
        update_review_queue_items(
            items,
            item_ids=[str(item.get("id", "")).strip() for item in filtered_items],
            review_status=args.status,
            review_notes=args.notes,
            append_notes=args.append_notes,
        )
        write_review_queue(items, queue_path)
        print()
        print(format_review_queue_report(summarize_review_queue(items), queue_path))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


def _add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--review-status",
        action="append",
        dest="review_statuses",
        default=None,
        help="Filter by current review_status. Can be repeated.",
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        default=None,
        help="Filter by category. Can be repeated.",
    )
    parser.add_argument(
        "--guard-status",
        action="append",
        dest="guard_statuses",
        default=None,
        help="Filter by suggested_guard.status. Can be repeated.",
    )
    parser.add_argument(
        "--recommendation",
        action="append",
        dest="recommendations",
        default=None,
        help="Filter by review_recommendation. Can be repeated.",
    )
    parser.add_argument(
        "--bulk-approval",
        action="append",
        dest="bulk_approval_recommendations",
        default=None,
        help="Filter by bulk_approval_recommendation. Can be repeated.",
    )
    parser.add_argument(
        "--validation",
        choices=("any", "valid", "invalid"),
        dest="validation_state",
        default="any",
        help="Filter by suggested_validation.valid state.",
    )
    parser.add_argument(
        "--parse-error",
        choices=("any", "yes", "no"),
        dest="parse_error_state",
        default="any",
        help="Filter by whether parse_error is present.",
    )


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "<none>"
    return " ".join(f"{key}={value}" for key, value in counts.items())


if __name__ == "__main__":
    raise SystemExit(main())
