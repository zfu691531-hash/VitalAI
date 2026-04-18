"""Run a lightweight user-overview HTTP smoke check against a running VitalAI API server."""

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


def run_user_overview_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_id: str = "elder-http-overview-smoke",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Seed the running API with one record per domain, then read the aggregated overview."""
    normalized_base_url = base_url.rstrip("/")
    health = _request_json(normalized_base_url, "/vitalai/health", timeout_seconds=timeout_seconds)

    seeded = {
        "profile_memory": _seed_profile_memory(normalized_base_url, user_id, timeout_seconds),
        "health": _seed_health(normalized_base_url, user_id, timeout_seconds),
        "daily_life": _seed_daily_life(normalized_base_url, user_id, timeout_seconds),
        "mental_care": _seed_mental_care(normalized_base_url, user_id, timeout_seconds),
    }
    overview = _request_json(
        normalized_base_url,
        f"/vitalai/users/{user_id}/overview",
        timeout_seconds=timeout_seconds,
    )

    ok = bool(
        health.get("status") == "ok"
        and all(bool(section["ok"]) for section in seeded.values())
        and _overview_is_ok(overview)
    )
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_id": user_id,
        "health_endpoint": health,
        "seeded": seeded,
        "overview": overview,
    }


def _seed_profile_memory(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/profile-memory",
        method="POST",
        payload={
            "source_agent": "overview-http-smoke",
            "user_id": user_id,
            "memory_key": "favorite_drink",
            "memory_value": "jasmine_tea",
            "trace_id": "trace-overview-http-profile",
        },
        timeout_seconds=timeout_seconds,
    )
    ok = bool(
        response.get("accepted") is True
        and response.get("profile_snapshot", {}).get("memory_count") == 1
    )
    return {"ok": ok, "response": response}


def _seed_health(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/health-alert",
        method="POST",
        payload={
            "source_agent": "overview-http-smoke",
            "user_id": user_id,
            "risk_level": "high",
            "trace_id": "trace-overview-http-health",
        },
        timeout_seconds=timeout_seconds,
    )
    entry = _as_dict(response.get("health_alert_entry"))
    ok = bool(
        response.get("accepted") is True
        and entry.get("risk_level") == "high"
        and entry.get("status") == "raised"
    )
    return {"ok": ok, "response": response}


def _seed_daily_life(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/daily-life-checkin",
        method="POST",
        payload={
            "source_agent": "overview-http-smoke",
            "user_id": user_id,
            "need": "meal_support",
            "urgency": "normal",
            "trace_id": "trace-overview-http-daily",
        },
        timeout_seconds=timeout_seconds,
    )
    entry = _as_dict(response.get("checkin_entry"))
    ok = bool(
        response.get("accepted") is True
        and entry.get("need") == "meal_support"
        and entry.get("urgency") == "normal"
    )
    return {"ok": ok, "response": response}


def _seed_mental_care(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/mental-care-checkin",
        method="POST",
        payload={
            "source_agent": "overview-http-smoke",
            "user_id": user_id,
            "mood_signal": "calm",
            "support_need": "emotional_checkin",
            "trace_id": "trace-overview-http-mental",
        },
        timeout_seconds=timeout_seconds,
    )
    entry = _as_dict(response.get("mental_care_entry"))
    ok = bool(
        response.get("accepted") is True
        and entry.get("mood_signal") == "calm"
        and entry.get("support_need") == "emotional_checkin"
    )
    return {"ok": ok, "response": response}


def _overview_is_ok(overview: dict[str, Any]) -> bool:
    sections = _as_dict(overview.get("overview"))
    profile_memory = _as_dict(sections.get("profile_memory"))
    health = _as_dict(sections.get("health"))
    daily_life = _as_dict(sections.get("daily_life"))
    mental_care = _as_dict(sections.get("mental_care"))
    recent_activity = overview.get("recent_activity")
    return bool(
        overview.get("accepted") is True
        and isinstance(recent_activity, list)
        and len(recent_activity) >= 4
        and int(profile_memory.get("memory_count", 0)) >= 1
        and int(health.get("alert_count", 0)) >= 1
        and int(daily_life.get("checkin_count", 0)) >= 1
        and int(mental_care.get("checkin_count", 0)) >= 1
    )


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for the overview smoke."""
    health_endpoint = _as_dict(report["health_endpoint"])
    overview = _as_dict(report["overview"])
    sections = _as_dict(overview["overview"])
    profile_memory = _as_dict(sections["profile_memory"])
    health = _as_dict(sections["health"])
    daily_life = _as_dict(sections["daily_life"])
    mental_care = _as_dict(sections["mental_care"])
    recent_activity = overview.get("recent_activity")
    latest_domain = "unknown"
    if isinstance(recent_activity, list) and recent_activity and isinstance(recent_activity[0], dict):
        latest_domain = str(recent_activity[0].get("domain", "unknown"))
    attention_items = overview.get("attention_items")
    top_attention_domain = "none"
    if isinstance(attention_items, list) and attention_items and isinstance(attention_items[0], dict):
        top_attention_domain = str(attention_items[0].get("domain", "none"))
    seeded = _as_dict(report["seeded"])
    lines = [
        f"VitalAI user overview HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"user_id: {report['user_id']}",
        f"health_endpoint: {_status(health_endpoint.get('status') == 'ok')} module={health_endpoint.get('module')}",
        f"seed_profile_memory: {_status(bool(seeded['profile_memory']['ok']))}",
        f"seed_health: {_status(bool(seeded['health']['ok']))}",
        f"seed_daily_life: {_status(bool(seeded['daily_life']['ok']))}",
        f"seed_mental_care: {_status(bool(seeded['mental_care']['ok']))}",
        (
            f"overview: {_status(_overview_is_ok(overview))} "
            f"profile_memory={profile_memory.get('memory_count')} "
            f"health={health.get('alert_count')} "
            f"daily_life={daily_life.get('checkin_count')} "
            f"mental_care={mental_care.get('checkin_count')} "
            f"latest_domain={latest_domain} "
            f"attention_count={0 if not isinstance(attention_items, list) else len(attention_items)} "
            f"top_attention_domain={top_attention_domain}"
        ),
    ]
    return "\n".join(lines)


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict report section, got {type(value).__name__}")
    return value


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> int:
    """Run the lightweight user overview smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check the lightweight user overview against one running VitalAI server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-id",
        default="elder-http-overview-smoke",
        help="User id used for the temporary overview smoke run.",
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
        report = run_user_overview_http_smoke(
            base_url=args.base_url,
            user_id=args.user_id,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.output == "text":
        print(format_text_report(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
