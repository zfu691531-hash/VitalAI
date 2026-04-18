"""Capture real second-layer response snapshots from configured second-layer backends."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_CASES_PATH = ROOT_DIR / "data" / "intent_eval" / "second_layer_capture_cases.jsonl"
DEFAULT_OUTPUT_PATH = ROOT_DIR / ".runtime" / "intent_eval" / "second_layer_captured_snapshots.jsonl"
_NULL_STREAM = open(os.devnull, "w", encoding="utf-8")
_INTENT_DECOMPOSITION_API: dict[str, Any] | None = None
DEFAULT_OPENAI_COMPATIBLE_CAPTURE_TIMEOUT_SECONDS = 5.0
DEFAULT_BASE_QWEN_CAPTURE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class CaptureConfig:
    provider: str = "openai_compatible"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.0
    timeout_seconds: float = 5.0


def load_capture_cases(cases_path: Path) -> list[dict[str, Any]]:
    """Load capture-case definitions from JSONL."""
    cases: list[dict[str, Any]] = []
    with cases_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} must be a JSON object.")
            cases.append(payload)
    return cases


def load_existing_capture_ids(output_path: Path) -> set[str]:
    """Load already captured case ids from an existing JSONL output file."""
    if not output_path.exists():
        return set()

    captured_ids: set[str] = set()
    with output_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Line {line_number} in {output_path} must be a JSON object.")
            case_id = payload.get("id")
            if case_id is None:
                continue
            captured_ids.add(str(case_id))
    return captured_ids


def select_capture_cases(
    cases: list[dict[str, Any]],
    *,
    case_ids: list[str] | None = None,
    categories: list[str] | None = None,
    limit: int | None = None,
    excluded_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter capture cases for one focused batch."""
    normalized_ids = [value.strip() for value in case_ids or [] if value and value.strip()]
    normalized_categories = [value.strip() for value in categories or [] if value and value.strip()]
    excluded_ids = set() if excluded_ids is None else {str(value) for value in excluded_ids}
    if limit is not None and limit <= 0:
        raise ValueError("Capture-case limit must be greater than 0.")

    if normalized_ids:
        available_ids = {str(case.get("id")) for case in cases}
        missing_ids = [value for value in normalized_ids if value not in available_ids]
        if missing_ids:
            raise ValueError(
                "Unknown capture-case id(s): " + ", ".join(sorted(dict.fromkeys(missing_ids)))
            )

    if normalized_categories:
        available_categories = {str(case.get("category", "uncategorized")) for case in cases}
        missing_categories = [
            value for value in normalized_categories if value not in available_categories
        ]
        if missing_categories:
            raise ValueError(
                "Unknown capture-case category(ies): "
                + ", ".join(sorted(dict.fromkeys(missing_categories)))
            )

    selected: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id"))
        category = str(case.get("category", "uncategorized"))
        if case_id in excluded_ids:
            continue
        if normalized_ids and case_id not in normalized_ids:
            continue
        if normalized_categories and category not in normalized_categories:
            continue
        selected.append(case)
        if limit is not None and len(selected) >= limit:
            break

    return selected


def capture_response_snapshots(
    cases: list[dict[str, Any]],
    *,
    config: CaptureConfig,
    client_factory: Any = OpenAI,
    base_llm_factory: Any | None = None,
) -> list[dict[str, Any]]:
    """Capture raw second-layer responses for one batch of cases."""
    api = _load_intent_decomposition_api()
    recognizer = api["RunUserIntentRecognitionUseCase"]()
    validator = api["RunIntentDecompositionValidationUseCase"]()
    guard_use_case = api["RunIntentDecompositionRoutingGuardUseCase"]()
    schema = api["intent_decomposition_llm_output_schema"]()
    client = None
    base_llm = None
    if config.provider == "base_qwen":
        base_llm = _build_base_qwen_capture_llm(
            config=config,
            base_llm_factory=base_llm_factory,
        )
    else:
        client = client_factory(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    records: list[dict[str, Any]] = []
    captured_at = datetime.now(timezone.utc).isoformat()
    for case in cases:
        command = api["UserInteractionCommand"](
            user_id=str(case.get("user_id", "intent-capture-user")),
            channel=str(case.get("channel", "offline_capture")),
            message=str(case["message"]),
            trace_id=str(case.get("trace_id", f"capture-{case['id']}")),
        )
        intent_result = recognizer.run(command)
        messages = api["build_intent_decomposition_llm_messages"](
            command=command,
            intent_result=intent_result,
            schema=schema,
        )
        request_error = None
        try:
            if config.provider == "base_qwen":
                raw_response_text = str(
                    base_llm.chat(
                        messages,
                        stream=False,
                        model=config.model,
                        temperature=config.temperature,
                    )
                )
            else:
                response = client.chat.completions.create(
                    model=config.model,
                    temperature=config.temperature,
                    messages=messages,
                )
                raw_response_text = api["extract_openai_compatible_response_text"](response)
        except Exception as exc:
            raw_response_text = ""
            request_error = f"{type(exc).__name__}: {exc}"

        parsed_payload = None
        parse_error = None
        validation_payload = None
        guard_payload = None
        if request_error is not None:
            parse_error = f"request_error: {request_error}"
        else:
            try:
                parsed_payload = api["parse_intent_decomposition_response_text"](raw_response_text)
                validation = validator.run(parsed_payload)
                validation_payload = api["intent_decomposition_validation_payload"](validation)
                if validation.valid and validation.result is not None:
                    guard_payload = api["intent_decomposition_routing_guard_payload"](
                        guard_use_case.run(validation.result)
                    )
            except ValueError as exc:
                parse_error = str(exc)

        records.append(
            {
                "id": str(case["id"]),
                "category": str(case.get("category", "uncategorized")),
                "description": str(case.get("description", "")),
                "message": command.message,
                "captured_at": captured_at,
                "request": {
                    "provider": config.provider,
                    "model": config.model,
                    "base_url": config.base_url,
                    "temperature": config.temperature,
                    "timeout_seconds": config.timeout_seconds,
                    "trace_id": command.trace_id,
                },
                "first_layer": api["intent_result_payload"](intent_result),
                "raw_response_text": raw_response_text,
                "parsed_payload": parsed_payload,
                "parse_error": parse_error,
                "request_error": request_error,
                "validation": validation_payload,
                "guard": guard_payload,
            }
        )
    return records


def write_capture_records(
    records: list[dict[str, Any]],
    output_path: Path,
    *,
    append: bool = False,
) -> None:
    """Write capture records to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def format_capture_summary(records: list[dict[str, Any]], output_path: Path) -> str:
    """Render a compact human-readable summary."""
    valid_count = sum(
        1
        for record in records
        if bool(((record.get("validation") or {})).get("valid"))
    )
    parse_failures = sum(1 for record in records if record.get("parse_error"))
    request_errors = sum(1 for record in records if record.get("request_error"))
    categories: dict[str, int] = {}
    for record in records:
        category = str(record.get("category", "uncategorized"))
        categories[category] = categories.get(category, 0) + 1
    categories_line = " ".join(f"{key}={value}" for key, value in sorted(categories.items())) or "<none>"
    return "\n".join(
        [
            "VitalAI second-layer snapshot capture: OK",
            f"output_path: {output_path}",
            f"records: total={len(records)} valid={valid_count} invalid={len(records) - valid_count}",
            f"parse_failures: {parse_failures}",
            f"request_errors: {request_errors}",
            f"categories: {categories_line}",
        ]
    )


def format_capture_case_listing(cases: list[dict[str, Any]]) -> str:
    """Render a compact list of the selected capture cases."""
    categories: dict[str, int] = {}
    for case in cases:
        category = str(case.get("category", "uncategorized"))
        categories[category] = categories.get(category, 0) + 1

    lines = [
        "VitalAI second-layer capture cases",
        f"selected_cases: {len(cases)}",
        "categories: " + (
            " ".join(f"{key}={value}" for key, value in sorted(categories.items())) or "<none>"
        ),
    ]
    for case in cases:
        lines.append(
            f"- {case.get('id')} [{case.get('category', 'uncategorized')}] "
            f"{case.get('description', '')}".rstrip()
        )
    return "\n".join(lines)


def format_empty_capture_selection(*, output_path: Path, skipped_existing: int) -> str:
    """Render a stable message when no capture cases remain to run."""
    return "\n".join(
        [
            "VitalAI second-layer snapshot capture: nothing to do",
            f"output_path: {output_path}",
            f"skipped_existing: {skipped_existing}",
            "records: total=0 valid=0 invalid=0",
        ]
    )


def capture_config_from_environment() -> CaptureConfig:
    """Build capture config from environment variables."""
    provider = _env_to_optional_str(os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER")) or "openai_compatible"
    model = _env_to_optional_str(os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_MODEL"))
    api_key = _env_to_optional_str(os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_API_KEY"))
    base_url = _env_to_optional_str(os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL"))
    if provider == "openai_compatible":
        model = model or _required_env("VITALAI_INTENT_DECOMPOSER_LLM_MODEL")
        api_key = api_key or _required_env("VITALAI_INTENT_DECOMPOSER_LLM_API_KEY")
        base_url = base_url or _required_env("VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL")
    return CaptureConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=_env_to_float(os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE"), default=0.0),
        timeout_seconds=_env_to_float(
            os.getenv("VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS"),
            default=_default_capture_timeout_seconds(provider),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """Capture one batch of second-layer response snapshots."""
    parser = argparse.ArgumentParser(
        description="Capture second-layer raw response snapshots from configured second-layer backends.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Path to the capture-case JSONL file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSONL path for captured snapshots.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the output file instead of overwriting it.",
    )
    parser.add_argument(
        "--id",
        dest="case_ids",
        action="append",
        default=[],
        help="Capture only the specified case id. Repeat to include multiple ids.",
    )
    parser.add_argument(
        "--category",
        dest="categories",
        action="append",
        default=[],
        help="Capture only the specified category. Repeat to include multiple categories.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of selected capture cases after filtering.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List the selected capture cases without calling the LLM backend.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip case ids that already exist in the output JSONL file.",
    )
    args = parser.parse_args(argv)

    output_path = args.output.resolve()
    existing_ids = load_existing_capture_ids(output_path) if args.skip_existing else set()
    cases = select_capture_cases(
        load_capture_cases(args.cases.resolve()),
        case_ids=args.case_ids,
        categories=args.categories,
        limit=args.limit,
        excluded_ids=existing_ids,
    )
    if args.list_cases:
        print(format_capture_case_listing(cases))
        return 0

    if not cases:
        print(
            format_empty_capture_selection(
                output_path=output_path,
                skipped_existing=len(existing_ids),
            )
        )
        return 0

    config = capture_config_from_environment()
    records = capture_response_snapshots(cases, config=config)
    write_capture_records(records, output_path, append=args.append)
    print(format_capture_summary(records, output_path))
    return 0


def _load_intent_decomposition_api() -> dict[str, Any]:
    """Lazily import intent-decomposition helpers without surfacing startup logs."""
    global _INTENT_DECOMPOSITION_API
    if _INTENT_DECOMPOSITION_API is None:
        with redirect_stdout(_NULL_STREAM), redirect_stderr(_NULL_STREAM):
            from VitalAI.application import (
                RunIntentDecompositionRoutingGuardUseCase,
                RunIntentDecompositionValidationUseCase,
                RunUserIntentRecognitionUseCase,
                UserInteractionCommand,
                build_intent_decomposition_llm_messages,
                extract_openai_compatible_response_text,
                intent_decomposition_llm_output_schema,
                intent_decomposition_routing_guard_payload,
                intent_decomposition_validation_payload,
                intent_result_payload,
                parse_intent_decomposition_response_text,
            )

        _INTENT_DECOMPOSITION_API = {
            "RunIntentDecompositionRoutingGuardUseCase": RunIntentDecompositionRoutingGuardUseCase,
            "RunIntentDecompositionValidationUseCase": RunIntentDecompositionValidationUseCase,
            "RunUserIntentRecognitionUseCase": RunUserIntentRecognitionUseCase,
            "UserInteractionCommand": UserInteractionCommand,
            "build_intent_decomposition_llm_messages": build_intent_decomposition_llm_messages,
            "extract_openai_compatible_response_text": extract_openai_compatible_response_text,
            "intent_decomposition_llm_output_schema": intent_decomposition_llm_output_schema,
            "intent_decomposition_routing_guard_payload": intent_decomposition_routing_guard_payload,
            "intent_decomposition_validation_payload": intent_decomposition_validation_payload,
            "intent_result_payload": intent_result_payload,
            "parse_intent_decomposition_response_text": parse_intent_decomposition_response_text,
        }
    return _INTENT_DECOMPOSITION_API


def _build_base_qwen_capture_llm(
    *,
    config: CaptureConfig,
    base_llm_factory: Any | None = None,
) -> Any:
    """Build one Base.Ai Qwen client for snapshot capture."""
    if base_llm_factory is not None:
        return base_llm_factory(config=config)
    if config.model or config.api_key or config.base_url:
        from Base.Ai.llms.qwenLlm import create_qwen_llm

        return create_qwen_llm(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            timeout=config.timeout_seconds,
        )
    from Base import get_default_qwen_llm

    llm = get_default_qwen_llm()
    if llm is None:
        raise ValueError("Base Qwen LLM is unavailable for capture.")
    return llm


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _env_to_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _env_to_float(value: str | None, *, default: float) -> float:
    if value is None:
        return default
    normalized = value.strip()
    if normalized == "":
        return default
    try:
        return float(normalized)
    except ValueError:
        return default


def _default_capture_timeout_seconds(provider: str) -> float:
    """Return a provider-aware default timeout for snapshot capture."""
    normalized_provider = provider.strip().lower().replace("-", "_")
    if normalized_provider == "base_qwen":
        return DEFAULT_BASE_QWEN_CAPTURE_TIMEOUT_SECONDS
    return DEFAULT_OPENAI_COMPATIBLE_CAPTURE_TIMEOUT_SECONDS


if __name__ == "__main__":
    raise SystemExit(main())
