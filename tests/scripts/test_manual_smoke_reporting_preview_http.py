"""Tests for the running-server reporting preview HTTP smoke script."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.manual_smoke_reporting_preview_http import (
    DEFAULT_BASE_URL,
    format_text_report,
    run_reporting_preview_http_smoke,
)


class ManualSmokeReportingPreviewHttpTests(unittest.TestCase):
    def test_run_reporting_preview_http_smoke_checks_real_preview_route(self) -> None:
        overview_report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "user_id": "report-user",
            "health_endpoint": {"status": "ok", "module": "VitalAI"},
            "seeded": {
                "profile_memory": {"ok": True, "response": {}},
                "health": {"ok": True, "response": {}},
                "daily_life": {"ok": True, "response": {}},
                "mental_care": {"ok": True, "response": {}},
            },
            "overview": {
                "accepted": True,
                "overview": {
                    "profile_memory": {"memory_count": 1},
                    "health": {"alert_count": 1},
                    "daily_life": {"checkin_count": 1},
                    "mental_care": {"checkin_count": 1},
                },
            },
        }
        report_preview = {
            "accepted": True,
            "execution_mode": "read_only_report_preview",
            "preview": {
                "title": "report-user overview report",
                "body": "latest_activity_at=...; attention=1 item; recent_domains=health, profile_memory",
                "source_lookup": {
                    "collaborator_agent_id": "tool-agent",
                    "tool_name": "user_overview_lookup",
                },
                "security_review": {
                    "reviewer_agent_id": "privacy-guardian-agent",
                },
            },
        }

        with patch(
            "scripts.manual_smoke_reporting_preview_http.run_user_overview_http_smoke",
            return_value=overview_report,
        ) as overview_mock, patch(
            "scripts.manual_smoke_reporting_preview_http._request_json",
            return_value=report_preview,
        ) as request_mock:
            report = run_reporting_preview_http_smoke(
                base_url=DEFAULT_BASE_URL,
                user_id="report-user",
                timeout_seconds=4.0,
            )

        overview_mock.assert_called_once_with(
            base_url=DEFAULT_BASE_URL,
            user_id="report-user",
            timeout_seconds=4.0,
        )
        request_mock.assert_called_once_with(
            DEFAULT_BASE_URL,
            "/vitalai/users/report-user/report-preview",
            timeout_seconds=4.0,
        )
        self.assertTrue(report["ok"])
        self.assertTrue(report["overview_smoke"]["ok"])
        self.assertTrue(report["report_preview"]["accepted"])

    def test_run_reporting_preview_http_smoke_marks_failed_preview(self) -> None:
        overview_report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "user_id": "elder-http-report-preview-smoke",
        }
        report_preview = {
            "accepted": True,
            "execution_mode": "read_only_report_preview",
            "preview": {
                "title": "elder-http-report-preview-smoke overview report",
                "body": "latest_activity_at=...; attention=1 item; recent_domains=health",
                "source_lookup": {
                    "collaborator_agent_id": "tool-agent",
                    "tool_name": "wrong_tool",
                },
                "security_review": {
                    "reviewer_agent_id": "privacy-guardian-agent",
                },
            },
        }

        with patch(
            "scripts.manual_smoke_reporting_preview_http.run_user_overview_http_smoke",
            return_value=overview_report,
        ), patch(
            "scripts.manual_smoke_reporting_preview_http._request_json",
            return_value=report_preview,
        ):
            report = run_reporting_preview_http_smoke()

        self.assertFalse(report["ok"])

    def test_format_text_report_summarizes_preview_chain(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "user_id": "report-user",
            "overview_smoke": {
                "ok": True,
            },
            "report_preview": {
                "accepted": True,
                "execution_mode": "read_only_report_preview",
                "preview": {
                    "title": "report-user overview report",
                    "body": "latest_activity_at=...; attention=1 item; recent_domains=health",
                    "source_lookup": {
                        "collaborator_agent_id": "tool-agent",
                        "tool_name": "user_overview_lookup",
                    },
                    "security_review": {
                        "reviewer_agent_id": "privacy-guardian-agent",
                    },
                },
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI reporting preview HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("user_id: report-user", text)
        self.assertIn("overview_smoke: OK", text)
        self.assertIn(
            "report_preview: OK title=report-user overview report lookup_agent=tool-agent privacy_agent=privacy-guardian-agent",
            text,
        )

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_reporting_preview_http.py",
                "--base-url",
                "http://127.0.0.1:9",
                "--timeout-seconds",
                "0.2",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("Could not reach VitalAI API", completed.stderr)


if __name__ == "__main__":
    unittest.main()
