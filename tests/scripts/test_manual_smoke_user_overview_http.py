"""Tests for the running-server user overview HTTP smoke script."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.manual_smoke_user_overview_http import (
    DEFAULT_BASE_URL,
    format_text_report,
    run_user_overview_http_smoke,
)


class ManualSmokeUserOverviewHttpTests(unittest.TestCase):
    def test_run_user_overview_http_smoke_seeds_domains_and_reads_overview(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("POST", "/vitalai/flows/profile-memory"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1},
            },
            ("POST", "/vitalai/flows/health-alert"): {
                "accepted": True,
                "health_alert_entry": {"risk_level": "high", "status": "raised"},
            },
            ("POST", "/vitalai/flows/daily-life-checkin"): {
                "accepted": True,
                "checkin_entry": {"need": "meal_support", "urgency": "normal"},
            },
            ("POST", "/vitalai/flows/mental-care-checkin"): {
                "accepted": True,
                "mental_care_entry": {"mood_signal": "calm", "support_need": "emotional_checkin"},
            },
            ("GET", "/vitalai/users/test-overview/overview"): {
                "accepted": True,
                "latest_activity_at": "2026-04-17T10:04:00+00:00",
                "attention_summary": "1 attention item(s) for test-overview.",
                "attention_items": [
                    {
                        "domain": "health",
                        "item_id": "1",
                        "severity": "high",
                        "summary": "Health alert high is still raised",
                    }
                ],
                "recent_activity": [
                    {
                        "domain": "mental_care",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:04:00+00:00",
                        "summary": "Mental-care calm (emotional_checkin)",
                    },
                    {
                        "domain": "daily_life",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:03:00+00:00",
                        "summary": "Daily-life meal_support (normal)",
                    },
                    {
                        "domain": "health",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:02:00+00:00",
                        "summary": "Health alert high (raised)",
                    },
                    {
                        "domain": "profile_memory",
                        "item_id": "favorite_drink",
                        "occurred_at": "2026-04-17T10:01:00+00:00",
                        "summary": "Memory favorite_drink=jasmine_tea",
                    }
                ],
                "overview": {
                    "profile_memory": {"memory_count": 1},
                    "health": {"alert_count": 1},
                    "daily_life": {"checkin_count": 1},
                    "mental_care": {"checkin_count": 1},
                },
            },
        }

        def fake_request_json(
            base_url: str,
            path: str,
            *,
            method: str = "GET",
            payload: dict[str, object] | None = None,
            query: dict[str, object] | None = None,
            timeout_seconds: float,
        ) -> dict[str, object]:
            self.assertEqual(DEFAULT_BASE_URL, base_url)
            self.assertEqual(4.0, timeout_seconds)
            self.assertIn(type(payload), {dict, type(None)})
            self.assertIn(type(query), {dict, type(None)})
            return responses[(method.upper(), path)]

        with patch("scripts.manual_smoke_user_overview_http._request_json", side_effect=fake_request_json):
            report = run_user_overview_http_smoke(
                base_url=DEFAULT_BASE_URL,
                user_id="test-overview",
                timeout_seconds=4.0,
            )

        self.assertTrue(report["ok"])
        self.assertTrue(report["seeded"]["profile_memory"]["ok"])
        self.assertTrue(report["seeded"]["health"]["ok"])
        self.assertTrue(report["seeded"]["daily_life"]["ok"])
        self.assertTrue(report["seeded"]["mental_care"]["ok"])
        self.assertTrue(report["overview"]["accepted"])

    def test_run_user_overview_http_smoke_marks_failed_overview(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("POST", "/vitalai/flows/profile-memory"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1},
            },
            ("POST", "/vitalai/flows/health-alert"): {
                "accepted": True,
                "health_alert_entry": {"risk_level": "high", "status": "raised"},
            },
            ("POST", "/vitalai/flows/daily-life-checkin"): {
                "accepted": True,
                "checkin_entry": {"need": "meal_support", "urgency": "normal"},
            },
            ("POST", "/vitalai/flows/mental-care-checkin"): {
                "accepted": True,
                "mental_care_entry": {"mood_signal": "calm", "support_need": "emotional_checkin"},
            },
            ("GET", "/vitalai/users/elder-http-overview-smoke/overview"): {
                "accepted": True,
                "latest_activity_at": "2026-04-17T10:04:00+00:00",
                "attention_summary": "1 attention item(s) for elder-http-overview-smoke.",
                "attention_items": [
                    {
                        "domain": "health",
                        "item_id": "1",
                        "severity": "high",
                        "summary": "Health alert high is still raised",
                    }
                ],
                "recent_activity": [
                    {
                        "domain": "mental_care",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:04:00+00:00",
                        "summary": "Mental-care calm (emotional_checkin)",
                    },
                    {
                        "domain": "daily_life",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:03:00+00:00",
                        "summary": "Daily-life meal_support (normal)",
                    },
                    {
                        "domain": "health",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:02:00+00:00",
                        "summary": "Health alert high (raised)",
                    },
                    {
                        "domain": "profile_memory",
                        "item_id": "favorite_drink",
                        "occurred_at": "2026-04-17T10:01:00+00:00",
                        "summary": "Memory favorite_drink=jasmine_tea",
                    }
                ],
                "overview": {
                    "profile_memory": {"memory_count": 1},
                    "health": {"alert_count": 1},
                    "daily_life": {"checkin_count": 0},
                    "mental_care": {"checkin_count": 1},
                },
            },
        }

        with patch(
            "scripts.manual_smoke_user_overview_http._request_json",
            side_effect=lambda base_url, path, **kwargs: responses[(kwargs.get("method", "GET").upper(), path)],
        ):
            report = run_user_overview_http_smoke()

        self.assertFalse(report["ok"])

    def test_format_text_report_summarizes_overview_counts(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "user_id": "overview-user",
            "health_endpoint": {"status": "ok", "module": "VitalAI"},
            "seeded": {
                "profile_memory": {"ok": True, "response": {}},
                "health": {"ok": True, "response": {}},
                "daily_life": {"ok": True, "response": {}},
                "mental_care": {"ok": True, "response": {}},
            },
            "overview": {
                "accepted": True,
                "latest_activity_at": "2026-04-17T10:04:00+00:00",
                "attention_summary": "1 attention item(s) for overview-user.",
                "attention_items": [
                    {
                        "domain": "health",
                        "item_id": "1",
                        "severity": "high",
                        "summary": "Health alert high is still raised",
                    }
                ],
                "recent_activity": [
                    {
                        "domain": "mental_care",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:04:00+00:00",
                        "summary": "Mental-care calm (emotional_checkin)",
                    },
                    {
                        "domain": "daily_life",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:03:00+00:00",
                        "summary": "Daily-life meal_support (normal)",
                    },
                    {
                        "domain": "health",
                        "item_id": "1",
                        "occurred_at": "2026-04-17T10:02:00+00:00",
                        "summary": "Health alert high (raised)",
                    },
                    {
                        "domain": "profile_memory",
                        "item_id": "favorite_drink",
                        "occurred_at": "2026-04-17T10:01:00+00:00",
                        "summary": "Memory favorite_drink=jasmine_tea",
                    }
                ],
                "overview": {
                    "profile_memory": {"memory_count": 1},
                    "health": {"alert_count": 1},
                    "daily_life": {"checkin_count": 1},
                    "mental_care": {"checkin_count": 1},
                },
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI user overview HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("user_id: overview-user", text)
        self.assertIn("seed_profile_memory: OK", text)
        self.assertIn("seed_health: OK", text)
        self.assertIn("seed_daily_life: OK", text)
        self.assertIn("seed_mental_care: OK", text)
        self.assertIn("overview: OK profile_memory=1 health=1 daily_life=1 mental_care=1", text)
        self.assertIn("latest_domain=mental_care", text)
        self.assertIn("attention_count=1", text)
        self.assertIn("top_attention_domain=health", text)

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_user_overview_http.py",
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
