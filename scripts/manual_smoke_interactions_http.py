"""Run a natural-language interactions HTTP smoke check against a running VitalAI API server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.manual_smoke_http_api import DEFAULT_BASE_URL, _request_json


def run_interactions_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_prefix: str = "elder-http-interactions-smoke",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Check the running HTTP server with a few high-value natural-language interaction cases."""
    normalized_base_url = base_url.rstrip("/")

    health = _request_json(normalized_base_url, "/vitalai/health", timeout_seconds=timeout_seconds)
    cases = {
        "health_route": _run_health_route_case(normalized_base_url, f"{user_prefix}-health", timeout_seconds),
        "profile_memory_route": _run_profile_memory_route_case(
            normalized_base_url,
            f"{user_prefix}-memory",
            timeout_seconds,
        ),
        "clarification_case": _run_clarification_case(
            normalized_base_url,
            f"{user_prefix}-clarify",
            timeout_seconds,
        ),
        "decomposition_case": _run_decomposition_case(
            normalized_base_url,
            f"{user_prefix}-decompose",
            timeout_seconds,
        ),
        "invalid_request_case": _run_invalid_request_case(normalized_base_url, timeout_seconds),
    }
    ok = bool(health.get("status") == "ok" and all(bool(case["ok"]) for case in cases.values()))
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_prefix": user_prefix,
        "health_endpoint": health,
        "cases": cases,
    }


def _run_health_route_case(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _post_interaction(
        base_url,
        payload={
            "user_id": user_id,
            "channel": "manual",
            "message": "I fell and feel dizzy now.",
            "trace_id": "trace-interactions-http-health",
            "source_agent": "interaction-http-smoke",
        },
        timeout_seconds=timeout_seconds,
    )
    intent = _as_dict(response.get("intent"))
    ok = bool(
        response.get("accepted") is True
        and response.get("routed_event_type") == "HEALTH_ALERT"
        and intent.get("primary_intent") == "health_alert"
    )
    return {"ok": ok, "user_id": user_id, "response": response}


def _run_profile_memory_route_case(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _post_interaction(
        base_url,
        payload={
            "user_id": user_id,
            "channel": "manual",
            "message": "Remember that I like jasmine tea.",
            "trace_id": "trace-interactions-http-profile",
            "source_agent": "interaction-http-smoke",
        },
        timeout_seconds=timeout_seconds,
    )
    intent = _as_dict(response.get("intent"))
    memory_updates = _as_dict(response.get("memory_updates"))
    stored_entry = _as_dict(memory_updates.get("stored_entry"))
    ok = bool(
        response.get("accepted") is True
        and response.get("routed_event_type") == "PROFILE_MEMORY_UPDATE"
        and intent.get("primary_intent") == "profile_memory_update"
        and stored_entry.get("memory_key") == "general_note"
    )
    return {"ok": ok, "user_id": user_id, "response": response}


def _run_clarification_case(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _post_interaction(
        base_url,
        payload={
            "user_id": user_id,
            "channel": "manual",
            "message": "hello",
            "trace_id": "trace-interactions-http-clarification",
            "source_agent": "interaction-http-smoke",
        },
        timeout_seconds=timeout_seconds,
    )
    intent = _as_dict(response.get("intent"))
    ok = bool(
        response.get("accepted") is False
        and response.get("error") == "clarification_needed"
        and intent.get("requires_clarification") is True
        and response.get("routed_event_type") is None
    )
    return {"ok": ok, "user_id": user_id, "response": response}


def _run_decomposition_case(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _post_interaction(
        base_url,
        payload={
            "user_id": user_id,
            "channel": "manual",
            "message": "I feel anxious but I also want to ask whether I should take that medicine every day.",
            "trace_id": "trace-interactions-http-decomposition",
            "source_agent": "interaction-http-smoke",
        },
        timeout_seconds=timeout_seconds,
    )
    error_details = _as_dict(response.get("error_details"))
    ok = bool(
        response.get("accepted") is False
        and response.get("error") == "decomposition_needed"
        and response.get("routed_event_type") is None
        and isinstance(error_details.get("decomposition"), dict)
        and isinstance(error_details.get("decomposition_guard"), dict)
    )
    return {"ok": ok, "user_id": user_id, "response": response}


def _run_invalid_request_case(base_url: str, timeout_seconds: float) -> dict[str, object]:
    response = _post_interaction(
        base_url,
        payload={
            "channel": "manual",
            "event_type": "health_alert",
        },
        timeout_seconds=timeout_seconds,
    )
    issues = response.get("error_details", {}).get("issues")
    ok = bool(
        response.get("accepted") is False
        and response.get("error") == "invalid_request"
        and _contains_issue(issues, field="user_id", code="required")
        and _contains_issue(issues, field="message", code="required")
    )
    return {"ok": ok, "response": response}


def _post_interaction(base_url: str, *, payload: dict[str, object], timeout_seconds: float) -> dict[str, Any]:
    return _request_json(
        base_url,
        "/vitalai/interactions",
        method="POST",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for natural-language interaction checks."""
    cases = _as_dict(report["cases"])
    health_endpoint = _as_dict(report["health_endpoint"])
    lines = [
        f"VitalAI interactions HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"health_endpoint: {_status(health_endpoint.get('status') == 'ok')} module={health_endpoint.get('module')}",
        _format_health_route_line(cases["health_route"]),
        _format_profile_memory_line(cases["profile_memory_route"]),
        _format_clarification_line(cases["clarification_case"]),
        _format_decomposition_line(cases["decomposition_case"]),
        _format_invalid_request_line(cases["invalid_request_case"]),
    ]
    return "\n".join(lines)


def _format_health_route_line(case: object) -> str:
    report = _as_dict(case)
    response = _as_dict(report["response"])
    intent = _as_dict(response["intent"])
    return (
        f"health_route: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"routed_event_type={response.get('routed_event_type')} "
        f"intent={intent.get('primary_intent')}"
    )


def _format_profile_memory_line(case: object) -> str:
    report = _as_dict(case)
    response = _as_dict(report["response"])
    memory_updates = _as_dict(response["memory_updates"])
    stored_entry = _as_dict(memory_updates["stored_entry"])
    return (
        f"profile_memory_route: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"routed_event_type={response.get('routed_event_type')} "
        f"memory_key={stored_entry.get('memory_key')}"
    )


def _format_clarification_line(case: object) -> str:
    report = _as_dict(case)
    response = _as_dict(report["response"])
    intent = _as_dict(response["intent"])
    return (
        f"clarification_case: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"error={response.get('error')} "
        f"requires_clarification={intent.get('requires_clarification')}"
    )


def _format_decomposition_line(case: object) -> str:
    report = _as_dict(case)
    response = _as_dict(report["response"])
    error_details = _as_dict(response["error_details"])
    decomposition_guard = _as_dict(error_details["decomposition_guard"])
    return (
        f"decomposition_case: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"error={response.get('error')} "
        f"guard_status={decomposition_guard.get('status')}"
    )


def _format_invalid_request_line(case: object) -> str:
    report = _as_dict(case)
    response = _as_dict(report["response"])
    issues = _issue_fields(response.get("error_details", {}).get("issues"))
    return (
        f"invalid_request_case: {_status(bool(report['ok']))} "
        f"error={response.get('error')} "
        f"issue_fields={','.join(issues)}"
    )


def _contains_issue(value: object, *, field: str, code: str) -> bool:
    if not isinstance(value, list):
        return False
    return any(
        isinstance(item, dict) and item.get("field") == field and item.get("code") == code
        for item in value
    )


def _issue_fields(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(
        str(item["field"])
        for item in value
        if isinstance(item, dict) and "field" in item
    )


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict report section, got {type(value).__name__}")
    return value


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> int:
    """Run the natural-language interactions HTTP smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check natural-language interactions against one running VitalAI server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-prefix",
        default="elder-http-interactions-smoke",
        help="User id prefix used for the temporary natural-language interaction cases.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="Report format. Defaults to json; text is easier for manual checks.",
    )
    args = parser.parse_args()

    try:
        report = run_interactions_http_smoke(
            base_url=args.base_url,
            user_prefix=args.user_prefix,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.output == "text":
        print(format_text_report(report))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if bool(report["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
