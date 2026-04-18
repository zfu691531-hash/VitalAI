"""Run a minimal HTTP smoke check against a running VitalAI API server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_BASE_URL = "http://127.0.0.1:8124"


def run_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_id: str = "elder-http-smoke-001",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Check the current HTTP server with one minimal write/read smoke flow."""
    normalized_base_url = base_url.rstrip("/")

    health = _request_json(normalized_base_url, "/vitalai/health", timeout_seconds=timeout_seconds)
    profile_write = _request_json(
        normalized_base_url,
        "/vitalai/flows/profile-memory",
        method="POST",
        payload={
            "source_agent": "http-smoke",
            "trace_id": "trace-http-smoke-profile-write",
            "user_id": user_id,
            "memory_key": "favorite_drink",
            "memory_value": "ginger_tea",
        },
        timeout_seconds=timeout_seconds,
    )
    profile_read = _request_json(
        normalized_base_url,
        f"/vitalai/flows/profile-memory/{user_id}",
        query={
            "source_agent": "http-smoke",
            "trace_id": "trace-http-smoke-profile-read",
            "memory_key": "favorite_drink",
        },
        timeout_seconds=timeout_seconds,
    )
    interaction = _request_json(
        normalized_base_url,
        "/vitalai/interactions",
        method="POST",
        payload={
            "user_id": user_id,
            "channel": "manual",
            "message": "帮我记住我喜欢喝姜茶",
            "trace_id": "trace-http-smoke-interaction",
            "source_agent": "http-smoke",
        },
        timeout_seconds=timeout_seconds,
    )

    ok = bool(
        health.get("status") == "ok"
        and profile_write.get("accepted") is True
        and profile_read.get("accepted") is True
        and interaction.get("accepted") is True
    )
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_id": user_id,
        "health": health,
        "profile_memory_write": profile_write,
        "profile_memory_read": profile_read,
        "interaction": interaction,
    }


def _request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    url = f"{base_url}{path}"
    if query:
        query_text = urlencode({key: str(value) for key, value in query.items()})
        url = f"{url}?{query_text}"

    data: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover - exercised by CLI behavior
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {method.upper()} {url}: {body}") from exc
    except URLError as exc:  # pragma: no cover - exercised by CLI behavior
        raise RuntimeError(
            f"Could not reach VitalAI API at {base_url}. Start the server first and retry."
        ) from exc


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable smoke report."""
    health = _as_dict(report["health"])
    profile_write = _as_dict(report["profile_memory_write"])
    profile_read = _as_dict(report["profile_memory_read"])
    interaction = _as_dict(report["interaction"])
    snapshot = _as_dict(profile_read["profile_snapshot"])
    interaction_intent = _as_dict(interaction["intent"])

    lines = [
        f"VitalAI HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"health: {_status(health.get('status') == 'ok')} module={health.get('module')}",
        (
            "profile_memory_write: "
            f"{_status(profile_write.get('accepted') is True)} "
            f"event_type={profile_write.get('event_type')} "
            f"memory_key={_get_nested(profile_write, 'stored_entry', 'memory_key')}"
        ),
        (
            "profile_memory_read: "
            f"{_status(profile_read.get('accepted') is True)} "
            f"memory_count={snapshot.get('memory_count')} "
            f"memory_keys={_join_values(snapshot.get('memory_keys'))}"
        ),
        (
            "interaction: "
            f"{_status(interaction.get('accepted') is True)} "
            f"routed_event_type={interaction.get('routed_event_type')} "
            f"intent={interaction_intent.get('primary_intent')}"
        ),
    ]
    return "\n".join(lines)


def _as_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict report section, got {type(value).__name__}")
    return value


def _get_nested(payload: dict[str, Any], *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _join_values(value: object) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> int:
    """Run the HTTP smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check one running VitalAI HTTP server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-id",
        default="elder-http-smoke-001",
        help="User id used for the temporary write/read smoke flow.",
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
        report = run_http_smoke(
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
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if bool(report["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
