"""Run a lightweight agent-registry HTTP smoke check against a running VitalAI API server."""

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


def run_agents_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_id: str = "elder-agent-http-smoke",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Exercise the lightweight agent registry and dry-run APIs on one running server."""
    normalized_base_url = base_url.rstrip("/")
    health = _request_json(normalized_base_url, "/vitalai/health", timeout_seconds=timeout_seconds)
    registry = _request_json(normalized_base_url, "/vitalai/agents", timeout_seconds=timeout_seconds)
    detail = _request_json(
        normalized_base_url,
        "/vitalai/agents/health-domain-agent",
        timeout_seconds=timeout_seconds,
    )
    domain_dry_run = _request_json(
        normalized_base_url,
        "/vitalai/agents/health-domain-agent/dry-run",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "trace_id": "trace-agent-http-health-dry-run",
            "user_id": f"{user_id}-health",
            "message": "dizzy and weak",
            "context": {"risk_level": "high"},
        },
        timeout_seconds=timeout_seconds,
    )
    privacy_dry_run = _request_json(
        normalized_base_url,
        "/vitalai/agents/privacy-guardian-agent/dry-run",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "payload": {
                "text": "Call me at 13812345678 or test@example.com",
                "api_key": "sk-secret-token",
            },
        },
        timeout_seconds=timeout_seconds,
    )
    seeded = {
        "profile_memory": _seed_profile_memory(normalized_base_url, user_id, timeout_seconds),
        "health": _seed_health(normalized_base_url, user_id, timeout_seconds),
    }
    tool_dry_run = _request_json(
        normalized_base_url,
        "/vitalai/agents/tool-agent/dry-run",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "trace_id": "trace-agent-http-tool-dry-run",
            "tool_name": "user_overview_lookup",
            "params": {
                "user_id": user_id,
                "history_limit": 3,
            },
        },
        timeout_seconds=timeout_seconds,
    )
    reporting_dry_run = _request_json(
        normalized_base_url,
        "/vitalai/agents/intelligent-reporting-agent/dry-run",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "trace_id": "trace-agent-http-reporting-dry-run",
            "user_id": user_id,
            "history_limit": 3,
        },
        timeout_seconds=timeout_seconds,
    )

    ok = bool(
        health.get("status") == "ok"
        and _registry_is_ok(registry)
        and _detail_is_ok(detail)
        and _domain_dry_run_is_ok(domain_dry_run)
        and _tool_dry_run_is_ok(tool_dry_run)
        and _privacy_dry_run_is_ok(privacy_dry_run)
        and all(bool(section["ok"]) for section in seeded.values())
        and _reporting_dry_run_is_ok(reporting_dry_run, user_id=user_id)
    )
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_id": user_id,
        "health_endpoint": health,
        "registry": registry,
        "detail": detail,
        "domain_dry_run": domain_dry_run,
        "tool_dry_run": tool_dry_run,
        "privacy_dry_run": privacy_dry_run,
        "seeded": seeded,
        "reporting_dry_run": reporting_dry_run,
    }


def _seed_profile_memory(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/profile-memory",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "trace_id": "trace-agent-http-profile-seed",
            "user_id": user_id,
            "memory_key": "favorite_drink",
            "memory_value": "jasmine_tea",
        },
        timeout_seconds=timeout_seconds,
    )
    snapshot = _as_dict(response.get("profile_snapshot"))
    ok = bool(response.get("accepted") is True and int(snapshot.get("memory_count", 0)) >= 1)
    return {"ok": ok, "response": response}


def _seed_health(base_url: str, user_id: str, timeout_seconds: float) -> dict[str, object]:
    response = _request_json(
        base_url,
        "/vitalai/flows/health-alert",
        method="POST",
        payload={
            "source_agent": "agent-http-smoke",
            "trace_id": "trace-agent-http-health-seed",
            "user_id": user_id,
            "risk_level": "high",
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


def _registry_is_ok(registry: dict[str, Any]) -> bool:
    agents = registry.get("agents")
    if not isinstance(agents, list):
        return False
    agent_ids = {
        item.get("agent_id")
        for item in agents
        if isinstance(item, dict)
    }
    required = {
        "health-domain-agent",
        "daily-life-domain-agent",
        "mental-care-domain-agent",
        "profile-memory-domain-agent",
        "intelligent-reporting-agent",
        "tool-agent",
        "privacy-guardian-agent",
    }
    return int(registry.get("count", 0)) >= 7 and required.issubset(agent_ids)


def _detail_is_ok(detail: dict[str, Any]) -> bool:
    agent = detail.get("agent")
    return bool(
        isinstance(agent, dict)
        and agent.get("agent_id") == "health-domain-agent"
        and agent.get("layer") == "domain"
    )


def _domain_dry_run_is_ok(report: dict[str, Any]) -> bool:
    dry_run = _as_dict(report.get("dry_run"))
    envelope = _as_dict(dry_run.get("envelope"))
    preview = _as_dict(dry_run.get("preview"))
    entry = _as_dict(preview.get("health_alert_entry"))
    return bool(
        dry_run.get("accepted") is True
        and envelope.get("to_agent") == "health-domain-agent"
        and entry.get("status") == "raised"
    )


def _tool_dry_run_is_ok(report: dict[str, Any]) -> bool:
    dry_run = _as_dict(report.get("dry_run"))
    preview = _as_dict(dry_run.get("preview"))
    result = _as_dict(preview.get("result"))
    return bool(
        dry_run.get("accepted") is True
        and dry_run.get("execution_mode") == "internal_tool_call"
        and preview.get("tool_name") == "user_overview_lookup"
        and preview.get("executed") is True
        and preview.get("external_call_executed") is False
        and result.get("user_id")
    )


def _privacy_dry_run_is_ok(report: dict[str, Any]) -> bool:
    dry_run = _as_dict(report.get("dry_run"))
    preview = _as_dict(dry_run.get("preview"))
    sanitized_payload = _as_dict(preview.get("sanitized_payload"))
    return bool(
        dry_run.get("accepted") is True
        and preview.get("action") == "REDACT"
        and sanitized_payload.get("api_key") == "[REDACTED]"
    )


def _reporting_dry_run_is_ok(report: dict[str, Any], *, user_id: str) -> bool:
    dry_run = _as_dict(report.get("dry_run"))
    preview = _as_dict(dry_run.get("preview"))
    security_review = _as_dict(preview.get("security_review"))
    source_lookup = _as_dict(preview.get("source_lookup"))
    return bool(
        dry_run.get("accepted") is True
        and preview.get("title") == f"{user_id} overview report"
        and isinstance(preview.get("body"), str)
        and "attention=" in preview.get("body", "")
        and source_lookup.get("collaborator_agent_id") == "tool-agent"
        and source_lookup.get("tool_name") == "user_overview_lookup"
        and security_review.get("reviewer_agent_id") == "privacy-guardian-agent"
    )


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for the agent smoke."""
    health_endpoint = _as_dict(report["health_endpoint"])
    registry = _as_dict(report["registry"])
    detail = _as_dict(report["detail"])
    domain_dry_run = _as_dict(report["domain_dry_run"])["dry_run"]
    tool_dry_run = _as_dict(report["tool_dry_run"])["dry_run"]
    privacy_dry_run = _as_dict(report["privacy_dry_run"])["dry_run"]
    reporting_dry_run = _as_dict(report["reporting_dry_run"])["dry_run"]
    seeded = _as_dict(report["seeded"])
    lines = [
        f"VitalAI agents HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"user_id: {report['user_id']}",
        f"health_endpoint: {_status(health_endpoint.get('status') == 'ok')} module={health_endpoint.get('module')}",
        f"agent_registry: {_status(_registry_is_ok(registry))} count={registry.get('count')}",
        f"agent_detail: {_status(_detail_is_ok(detail))} agent_id={detail.get('agent', {}).get('agent_id') if isinstance(detail.get('agent'), dict) else 'unknown'}",
        f"health_domain_dry_run: {_status(_domain_dry_run_is_ok(_as_dict(report['domain_dry_run'])))}",
        (
            "tool_dry_run: "
            f"{_status(_tool_dry_run_is_ok(_as_dict(report['tool_dry_run'])))} "
            f"tool={_as_dict(tool_dry_run.get('preview', {})).get('tool_name')} "
            f"mode={tool_dry_run.get('execution_mode')}"
        ),
        f"privacy_dry_run: {_status(_privacy_dry_run_is_ok(_as_dict(report['privacy_dry_run'])))} action={_as_dict(privacy_dry_run.get('preview', {})).get('action')}",
        f"seed_profile_memory: {_status(bool(seeded['profile_memory']['ok']))}",
        f"seed_health: {_status(bool(seeded['health']['ok']))}",
        (
            "reporting_dry_run: "
            f"{_status(_reporting_dry_run_is_ok(_as_dict(report['reporting_dry_run']), user_id=str(report['user_id'])))} "
            f"title={_as_dict(reporting_dry_run.get('preview', {})).get('title')} "
            f"lookup_agent={_as_dict(_as_dict(reporting_dry_run.get('preview', {})).get('source_lookup', {})).get('collaborator_agent_id')} "
            f"privacy_action={_as_dict(_as_dict(reporting_dry_run.get('preview', {})).get('security_review', {})).get('action')}"
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
    """Run the lightweight agent-registry smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check the lightweight agent registry against one running VitalAI server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-id",
        default="elder-agent-http-smoke",
        help="User id used for the temporary agent smoke run.",
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
        report = run_agents_http_smoke(
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
