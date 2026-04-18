"""Run a typed-flow HTTP smoke check against a running VitalAI API server."""

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


def run_typed_flow_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_prefix: str = "elder-http-typed-smoke",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Check the current HTTP server with write/read loops for the four typed flows."""
    normalized_base_url = base_url.rstrip("/")

    profile_memory_user_id = f"{user_prefix}-profile"
    health_user_id = f"{user_prefix}-health"
    daily_life_user_id = f"{user_prefix}-daily"
    mental_care_user_id = f"{user_prefix}-mental"

    health = _request_json(normalized_base_url, "/vitalai/health", timeout_seconds=timeout_seconds)
    profile_memory = _run_profile_memory_flow(normalized_base_url, profile_memory_user_id, timeout_seconds)
    health_alert = _run_health_alert_flow(normalized_base_url, health_user_id, timeout_seconds)
    daily_life = _run_daily_life_flow(normalized_base_url, daily_life_user_id, timeout_seconds)
    mental_care = _run_mental_care_flow(normalized_base_url, mental_care_user_id, timeout_seconds)

    flows = {
        "profile_memory": profile_memory,
        "health": health_alert,
        "daily_life": daily_life,
        "mental_care": mental_care,
    }
    ok = bool(health.get("status") == "ok" and all(bool(flow["ok"]) for flow in flows.values()))
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_prefix": user_prefix,
        "health_endpoint": health,
        "flows": flows,
    }


def _run_profile_memory_flow(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    write = _request_json(
        base_url,
        "/vitalai/flows/profile-memory",
        method="POST",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-profile-write",
            "user_id": user_id,
            "memory_key": "favorite_drink",
            "memory_value": "ginger_tea",
        },
        timeout_seconds=timeout_seconds,
    )
    read = _request_json(
        base_url,
        f"/vitalai/flows/profile-memory/{user_id}",
        query={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-profile-read",
            "memory_key": "favorite_drink",
        },
        timeout_seconds=timeout_seconds,
    )
    snapshot = _as_dict(read.get("profile_snapshot"))
    memory_keys = snapshot.get("memory_keys")
    ok = bool(
        write.get("accepted") is True
        and read.get("accepted") is True
        and snapshot.get("memory_count") == 1
        and isinstance(memory_keys, list)
        and "favorite_drink" in memory_keys
    )
    return {
        "ok": ok,
        "user_id": user_id,
        "write": write,
        "read": read,
    }


def _run_health_alert_flow(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    write = _request_json(
        base_url,
        "/vitalai/flows/health-alert",
        method="POST",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-health-write",
            "user_id": user_id,
            "risk_level": "high",
        },
        timeout_seconds=timeout_seconds,
    )
    alert_id = _as_dict(write.get("health_alert_entry")).get("alert_id")
    acknowledge = _request_json(
        base_url,
        f"/vitalai/flows/health-alerts/{user_id}/{alert_id}/acknowledge",
        method="PATCH",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-health-acknowledge",
        },
        timeout_seconds=timeout_seconds,
    )
    resolve = _request_json(
        base_url,
        f"/vitalai/flows/health-alerts/{user_id}/{alert_id}/resolve",
        method="PATCH",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-health-resolve",
        },
        timeout_seconds=timeout_seconds,
    )
    read = _request_json(
        base_url,
        f"/vitalai/flows/health-alerts/{user_id}",
        query={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-health-read",
            "limit": 10,
        },
        timeout_seconds=timeout_seconds,
    )
    snapshot = _as_dict(read.get("health_alert_snapshot"))
    recent_risk_levels = snapshot.get("recent_risk_levels")
    entries = snapshot.get("entries")
    latest_status = None
    if isinstance(entries, list) and entries:
        latest_status = _as_dict(entries[0]).get("status")
    ok = bool(
        write.get("accepted") is True
        and acknowledge.get("accepted") is True
        and acknowledge.get("current_status") == "acknowledged"
        and resolve.get("accepted") is True
        and resolve.get("current_status") == "resolved"
        and read.get("accepted") is True
        and int(snapshot.get("alert_count", 0)) >= 1
        and isinstance(recent_risk_levels, list)
        and len(recent_risk_levels) >= 1
        and recent_risk_levels[0] == "high"
        and latest_status == "resolved"
    )
    return {
        "ok": ok,
        "user_id": user_id,
        "write": write,
        "acknowledge": acknowledge,
        "resolve": resolve,
        "read": read,
    }


def _run_daily_life_flow(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    write = _request_json(
        base_url,
        "/vitalai/flows/daily-life-checkin",
        method="POST",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-daily-write",
            "user_id": user_id,
            "need": "meal_support",
            "urgency": "normal",
        },
        timeout_seconds=timeout_seconds,
    )
    read = _request_json(
        base_url,
        f"/vitalai/flows/daily-life-checkins/{user_id}",
        query={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-daily-read",
            "limit": 10,
        },
        timeout_seconds=timeout_seconds,
    )
    snapshot = _as_dict(read.get("daily_life_snapshot"))
    recent_needs = snapshot.get("recent_needs")
    ok = bool(
        write.get("accepted") is True
        and read.get("accepted") is True
        and int(snapshot.get("checkin_count", 0)) >= 1
        and isinstance(recent_needs, list)
        and len(recent_needs) >= 1
        and recent_needs[0] == "meal_support"
    )
    return {
        "ok": ok,
        "user_id": user_id,
        "write": write,
        "read": read,
    }


def _run_mental_care_flow(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    write = _request_json(
        base_url,
        "/vitalai/flows/mental-care-checkin",
        method="POST",
        payload={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-mental-write",
            "user_id": user_id,
            "mood_signal": "calm",
            "support_need": "companionship",
        },
        timeout_seconds=timeout_seconds,
    )
    read = _request_json(
        base_url,
        f"/vitalai/flows/mental-care-checkins/{user_id}",
        query={
            "source_agent": "typed-http-smoke",
            "trace_id": "trace-typed-http-smoke-mental-read",
            "limit": 10,
        },
        timeout_seconds=timeout_seconds,
    )
    snapshot = _as_dict(read.get("mental_care_snapshot"))
    recent_mood_signals = snapshot.get("recent_mood_signals")
    recent_support_needs = snapshot.get("recent_support_needs")
    ok = bool(
        write.get("accepted") is True
        and read.get("accepted") is True
        and int(snapshot.get("checkin_count", 0)) >= 1
        and isinstance(recent_mood_signals, list)
        and len(recent_mood_signals) >= 1
        and recent_mood_signals[0] == "calm"
        and isinstance(recent_support_needs, list)
        and len(recent_support_needs) >= 1
        and recent_support_needs[0] == "companionship"
    )
    return {
        "ok": ok,
        "user_id": user_id,
        "write": write,
        "read": read,
    }


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for the running-server typed flows."""
    flows = _as_dict(report["flows"])
    health_endpoint = _as_dict(report["health_endpoint"])

    lines = [
        f"VitalAI typed-flow HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"health_endpoint: {_status(health_endpoint.get('status') == 'ok')} module={health_endpoint.get('module')}",
        _format_profile_memory_line(flows["profile_memory"]),
        _format_health_line(flows["health"]),
        _format_daily_life_line(flows["daily_life"]),
        _format_mental_care_line(flows["mental_care"]),
    ]
    return "\n".join(lines)


def _format_profile_memory_line(flow: object) -> str:
    report = _as_dict(flow)
    snapshot = _as_dict(_as_dict(report["read"])["profile_snapshot"])
    return (
        f"profile_memory: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"memory_count={snapshot.get('memory_count')} "
        f"memory_keys={_join_values(snapshot.get('memory_keys'))}"
    )


def _format_health_line(flow: object) -> str:
    report = _as_dict(flow)
    snapshot = _as_dict(_as_dict(report["read"])["health_alert_snapshot"])
    latest_entry = {}
    if snapshot.get("entries"):
        latest_entry = _as_dict(snapshot["entries"][0])
    return (
        f"health: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"alert_count={snapshot.get('alert_count')} "
        f"recent_risk_levels={_join_values(snapshot.get('recent_risk_levels'))} "
        f"status={latest_entry.get('status')}"
    )


def _format_daily_life_line(flow: object) -> str:
    report = _as_dict(flow)
    snapshot = _as_dict(_as_dict(report["read"])["daily_life_snapshot"])
    return (
        f"daily_life: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"checkin_count={snapshot.get('checkin_count')} "
        f"recent_needs={_join_values(snapshot.get('recent_needs'))}"
    )


def _format_mental_care_line(flow: object) -> str:
    report = _as_dict(flow)
    snapshot = _as_dict(_as_dict(report["read"])["mental_care_snapshot"])
    return (
        f"mental_care: {_status(bool(report['ok']))} "
        f"user_id={report['user_id']} "
        f"checkin_count={snapshot.get('checkin_count')} "
        f"recent_mood_signals={_join_values(snapshot.get('recent_mood_signals'))} "
        f"recent_support_needs={_join_values(snapshot.get('recent_support_needs'))}"
    )


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict report section, got {type(value).__name__}")
    return value


def _join_values(value: object) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> int:
    """Run the typed-flow HTTP smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check typed HTTP flows against one running VitalAI server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-prefix",
        default="elder-http-typed-smoke",
        help="User id prefix used for the temporary typed-flow write/read loops.",
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
        report = run_typed_flow_http_smoke(
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
