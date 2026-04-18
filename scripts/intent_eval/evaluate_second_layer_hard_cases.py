"""Offline evaluation for second-layer decomposition hard cases and response snapshots."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_DATASET_PATH = ROOT_DIR / "data" / "intent_eval" / "second_layer_hard_cases.jsonl"
_NULL_STREAM = open(os.devnull, "w", encoding="utf-8")
_INTENT_DECOMPOSITION_API: tuple[type[Any], type[Any], Any] | None = None


@dataclass(frozen=True)
class EvaluatedSample:
    sample_id: str
    category: str
    input_kind: str
    valid: bool
    routing_decision: str
    risk_flags: tuple[str, ...]
    guard_status: str | None
    blocked_reasons: tuple[str, ...]
    issue_codes: tuple[str, ...]
    parse_error: str | None
    expectation_passed: bool


def load_samples(dataset_path: Path) -> list[dict[str, Any]]:
    """Load JSONL hard-case or response-snapshot samples."""
    samples: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} must be a JSON object.")
            samples.append(payload)
    return samples


def evaluate_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate and guard each hard-case sample, then aggregate summary stats."""
    validation_use_case_type, guard_use_case_type, parse_response_text = _load_intent_decomposition_api()
    validator = validation_use_case_type()
    guard_use_case = guard_use_case_type()

    input_kinds: Counter[str] = Counter()
    routing_decisions: Counter[str] = Counter()
    risk_flags: Counter[str] = Counter()
    guard_statuses: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    results: list[EvaluatedSample] = []

    for sample in samples:
        categories[str(sample["category"])] += 1
        input_kind, raw_payload, parse_error = _resolve_sample_payload(
            sample,
            parse_response_text=parse_response_text,
        )
        input_kinds[input_kind] += 1

        routing_decision = _raw_routing_decision(raw_payload) if parse_error is None else "<parse_failed>"
        routing_decisions[routing_decision] += 1

        for risk_flag_key in _raw_risk_flag_keys(raw_payload):
            risk_flags[risk_flag_key] += 1

        if parse_error is None:
            validation = validator.run(raw_payload)
            issue_codes = tuple(issue.code for issue in validation.issues)
            validation_valid = validation.valid
        else:
            validation = None
            issue_codes = ("parse_error",)
            validation_valid = False

        guard_status = None
        blocked_reasons: tuple[str, ...] = ()
        if validation is not None and validation.valid and validation.result is not None:
            guard = guard_use_case.run(validation.result)
            guard_status = guard.status
            guard_statuses[guard.status] += 1
            blocked_reasons = tuple(guard.blocked_reasons)

        evaluated = EvaluatedSample(
            sample_id=str(sample["id"]),
            category=str(sample["category"]),
            input_kind=input_kind,
            valid=validation_valid,
            routing_decision=routing_decision,
            risk_flags=tuple(_raw_risk_flag_keys(raw_payload)),
            guard_status=guard_status,
            blocked_reasons=blocked_reasons,
            issue_codes=issue_codes,
            parse_error=parse_error,
            expectation_passed=_expectation_passed(
                sample["expected"],
                validation_valid=validation_valid,
                guard_status=guard_status,
                blocked_reasons=blocked_reasons,
                issue_codes=issue_codes,
                parse_error=parse_error,
            ),
        )
        results.append(evaluated)

    expectation_failures = [result for result in results if not result.expectation_passed]
    return {
        "dataset_path": str(DEFAULT_DATASET_PATH),
        "total_samples": len(results),
        "input_kind_counts": dict(sorted(input_kinds.items())),
        "valid_samples": sum(1 for result in results if result.valid),
        "invalid_samples": sum(1 for result in results if not result.valid),
        "parse_failure_count": sum(1 for result in results if result.parse_error is not None),
        "routing_decision_counts": dict(sorted(routing_decisions.items())),
        "risk_flag_counts": dict(sorted(risk_flags.items())),
        "guard_status_counts": dict(sorted(guard_statuses.items())),
        "category_counts": dict(sorted(categories.items())),
        "expectation_failure_count": len(expectation_failures),
        "failed_sample_ids": [result.sample_id for result in expectation_failures],
        "samples": [
            {
                "id": result.sample_id,
                "category": result.category,
                "input_kind": result.input_kind,
                "valid": result.valid,
                "routing_decision": result.routing_decision,
                "risk_flags": list(result.risk_flags),
                "guard_status": result.guard_status,
                "blocked_reasons": list(result.blocked_reasons),
                "issue_codes": list(result.issue_codes),
                "parse_error": result.parse_error,
                "expectation_passed": result.expectation_passed,
            }
            for result in results
        ],
    }


def format_text_report(summary: dict[str, Any]) -> str:
    """Render a compact human-readable report."""
    lines = [
        "VitalAI second-layer hard-case eval: "
        + ("OK" if summary["expectation_failure_count"] == 0 else "FAILED"),
        f"dataset_path: {summary['dataset_path']}",
        (
            "samples: "
            f"total={summary['total_samples']} "
            f"valid={summary['valid_samples']} "
            f"invalid={summary['invalid_samples']}"
        ),
        "input_kinds: " + _format_counter_line(summary["input_kind_counts"]),
        f"parse_failures: {summary['parse_failure_count']}",
        "routing_decisions: " + _format_counter_line(summary["routing_decision_counts"]),
        "risk_flags: " + _format_counter_line(summary["risk_flag_counts"]),
        "guard_statuses: " + _format_counter_line(summary["guard_status_counts"]),
        "categories: " + _format_counter_line(summary["category_counts"]),
        f"expectation_failures: {summary['expectation_failure_count']}",
    ]
    if summary["failed_sample_ids"]:
        lines.append("failed_sample_ids: " + ",".join(summary["failed_sample_ids"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the offline hard-case evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate second-layer decomposition hard cases and response snapshots offline.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the hard-case or response-snapshot JSONL dataset.",
    )
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    dataset_path = args.dataset.resolve()
    samples = load_samples(dataset_path)
    summary = evaluate_samples(samples)
    summary["dataset_path"] = str(dataset_path)

    if args.output == "text":
        print(format_text_report(summary))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["expectation_failure_count"] == 0 else 1


def _load_intent_decomposition_api() -> tuple[type[Any], type[Any], Any]:
    """Lazily import intent-decomposition API without surfacing startup log noise."""
    global _INTENT_DECOMPOSITION_API
    if _INTENT_DECOMPOSITION_API is None:
        with redirect_stdout(_NULL_STREAM), redirect_stderr(_NULL_STREAM):
            from VitalAI.application import (
                RunIntentDecompositionRoutingGuardUseCase,
                RunIntentDecompositionValidationUseCase,
                parse_intent_decomposition_response_text,
            )

        _INTENT_DECOMPOSITION_API = (
            RunIntentDecompositionValidationUseCase,
            RunIntentDecompositionRoutingGuardUseCase,
            parse_intent_decomposition_response_text,
        )
    return _INTENT_DECOMPOSITION_API


def _resolve_sample_payload(
    sample: dict[str, Any],
    *,
    parse_response_text: Any,
) -> tuple[str, Any, str | None]:
    raw_payload = sample.get("raw_payload")
    if raw_payload is not None:
        return "raw_payload", raw_payload, None
    raw_response_text = sample.get("raw_response_text")
    if isinstance(raw_response_text, str):
        try:
            return "raw_response_text", parse_response_text(raw_response_text), None
        except ValueError as exc:
            return "raw_response_text", None, str(exc)
    raise ValueError(f"Sample {sample.get('id', '<unknown>')} must contain raw_payload or raw_response_text.")


def _raw_routing_decision(raw_payload: Any) -> str:
    if isinstance(raw_payload, dict):
        value = raw_payload.get("routing_decision")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "<missing>"


def _raw_risk_flag_keys(raw_payload: Any) -> list[str]:
    if not isinstance(raw_payload, dict):
        return []
    raw_flags = raw_payload.get("risk_flags", [])
    if not isinstance(raw_flags, list):
        return []
    keys: list[str] = []
    for raw_flag in raw_flags:
        if not isinstance(raw_flag, dict):
            continue
        kind = raw_flag.get("kind")
        severity = raw_flag.get("severity")
        if isinstance(kind, str) and isinstance(severity, str):
            keys.append(f"{kind}:{severity}")
    return keys


def _expectation_passed(
    expected: Any,
    *,
    validation_valid: bool,
    guard_status: str | None,
    blocked_reasons: tuple[str, ...],
    issue_codes: tuple[str, ...],
    parse_error: str | None,
) -> bool:
    if not isinstance(expected, dict):
        return False
    expected_valid = expected.get("valid")
    if expected_valid is not validation_valid:
        return False
    expected_parse_error_contains = expected.get("parse_error_contains")
    if expected_parse_error_contains is not None:
        return parse_error is not None and str(expected_parse_error_contains) in parse_error
    if validation_valid:
        if expected.get("guard_status") != guard_status:
            return False
        expected_blocked = expected.get("blocked_reasons", [])
        if sorted(str(item) for item in expected_blocked) != sorted(blocked_reasons):
            return False
        return True
    expected_issue_codes = {str(item) for item in expected.get("issue_codes", [])}
    return expected_issue_codes.issubset(set(issue_codes))


def _format_counter_line(counter_payload: dict[str, int]) -> str:
    if not counter_payload:
        return "<none>"
    return " ".join(f"{key}={value}" for key, value in counter_payload.items())


if __name__ == "__main__":
    raise SystemExit(main())
