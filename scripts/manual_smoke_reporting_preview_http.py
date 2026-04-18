"""Run a lightweight reporting-preview HTTP smoke check against a running VitalAI API server."""

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
from scripts.manual_smoke_user_overview_http import run_user_overview_http_smoke


def run_reporting_preview_http_smoke(
    *,
    base_url: str = DEFAULT_BASE_URL,
    user_id: str = "elder-http-report-preview-smoke",
    timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Seed one user overview, then verify the real reporting preview endpoint."""
    overview_report = run_user_overview_http_smoke(
        base_url=base_url,
        user_id=user_id,
        timeout_seconds=timeout_seconds,
    )
    normalized_base_url = str(overview_report["base_url"])
    report_preview = _request_json(
        normalized_base_url,
        f"/vitalai/users/{user_id}/report-preview",
        timeout_seconds=timeout_seconds,
    )
    ok = bool(overview_report["ok"] and _report_preview_is_ok(report_preview, user_id=user_id))
    return {
        "ok": ok,
        "base_url": normalized_base_url,
        "user_id": user_id,
        "overview_smoke": overview_report,
        "report_preview": report_preview,
    }


def _report_preview_is_ok(report_preview: dict[str, Any], *, user_id: str) -> bool:
    preview = _as_dict(report_preview.get("preview"))
    source_lookup = _as_dict(preview.get("source_lookup"))
    security_review = _as_dict(preview.get("security_review"))
    return bool(
        report_preview.get("accepted") is True
        and report_preview.get("execution_mode") == "read_only_report_preview"
        and preview.get("title") == f"{user_id} overview report"
        and isinstance(preview.get("body"), str)
        and "attention=" in preview.get("body", "")
        and source_lookup.get("collaborator_agent_id") == "tool-agent"
        and source_lookup.get("tool_name") == "user_overview_lookup"
        and security_review.get("reviewer_agent_id") == "privacy-guardian-agent"
    )


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for the reporting preview smoke."""
    overview_smoke = _as_dict(report["overview_smoke"])
    report_preview = _as_dict(report["report_preview"])
    preview = _as_dict(report_preview["preview"])
    source_lookup = _as_dict(preview["source_lookup"])
    security_review = _as_dict(preview["security_review"])
    lines = [
        f"VitalAI reporting preview HTTP smoke: {_status(bool(report['ok']))}",
        f"base_url: {report['base_url']}",
        f"user_id: {report['user_id']}",
        f"overview_smoke: {_status(bool(overview_smoke['ok']))}",
        (
            f"report_preview: {_status(_report_preview_is_ok(report_preview, user_id=str(report['user_id'])))} "
            f"title={preview.get('title')} "
            f"lookup_agent={source_lookup.get('collaborator_agent_id')} "
            f"privacy_agent={security_review.get('reviewer_agent_id')}"
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
    """Run the lightweight reporting preview smoke check from the command line."""
    parser = argparse.ArgumentParser(description="Smoke-check the real reporting preview endpoint against one running VitalAI server.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"VitalAI base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--user-id",
        default="elder-http-report-preview-smoke",
        help="User id used for the temporary reporting preview smoke run.",
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
        report = run_reporting_preview_http_smoke(
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
