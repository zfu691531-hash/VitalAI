"""Tests for the running-server typed-flow HTTP smoke script."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.manual_smoke_typed_flow_http import DEFAULT_BASE_URL, format_text_report, run_typed_flow_http_smoke


class ManualSmokeTypedFlowHttpTests(unittest.TestCase):
    def test_run_typed_flow_http_smoke_checks_all_four_flows(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("POST", "/vitalai/flows/profile-memory"): {"accepted": True},
            ("GET", "/vitalai/flows/profile-memory/test-prefix-profile"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1, "memory_keys": ["favorite_drink"]},
            },
            ("POST", "/vitalai/flows/health-alert"): {"accepted": True},
            ("PATCH", "/vitalai/flows/health-alerts/test-prefix-health/7/acknowledge"): {
                "accepted": True,
                "current_status": "acknowledged",
            },
            ("PATCH", "/vitalai/flows/health-alerts/test-prefix-health/7/resolve"): {
                "accepted": True,
                "current_status": "resolved",
            },
            ("GET", "/vitalai/flows/health-alerts/test-prefix-health"): {
                "accepted": True,
                "health_alert_snapshot": {
                    "alert_count": 1,
                    "recent_risk_levels": ["high"],
                    "entries": [{"status": "resolved"}],
                },
            },
            ("POST", "/vitalai/flows/daily-life-checkin"): {"accepted": True},
            ("GET", "/vitalai/flows/daily-life-checkins/test-prefix-daily"): {
                "accepted": True,
                "daily_life_snapshot": {"checkin_count": 1, "recent_needs": ["meal_support"]},
            },
            ("POST", "/vitalai/flows/mental-care-checkin"): {"accepted": True},
            ("GET", "/vitalai/flows/mental-care-checkins/test-prefix-mental"): {
                "accepted": True,
                "mental_care_snapshot": {
                    "checkin_count": 1,
                    "recent_mood_signals": ["calm"],
                    "recent_support_needs": ["companionship"],
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
            self.assertEqual(3.0, timeout_seconds)
            if payload is not None:
                self.assertIsInstance(payload, dict)
            if query is not None:
                self.assertIsInstance(query, dict)
            if path == "/vitalai/flows/health-alert":
                return {"accepted": True, "health_alert_entry": {"alert_id": 7}}
            return responses[(method.upper(), path)]

        with patch("scripts.manual_smoke_typed_flow_http._request_json", side_effect=fake_request_json):
            report = run_typed_flow_http_smoke(
                base_url=DEFAULT_BASE_URL,
                user_prefix="test-prefix",
                timeout_seconds=3.0,
            )

        self.assertTrue(report["ok"])
        flows = report["flows"]
        self.assertTrue(flows["profile_memory"]["ok"])
        self.assertTrue(flows["health"]["ok"])
        self.assertTrue(flows["daily_life"]["ok"])
        self.assertTrue(flows["mental_care"]["ok"])

    def test_run_typed_flow_http_smoke_marks_failed_flow(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("POST", "/vitalai/flows/profile-memory"): {"accepted": True},
            ("GET", "/vitalai/flows/profile-memory/test-prefix-profile"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 0, "memory_keys": []},
            },
            ("POST", "/vitalai/flows/health-alert"): {"accepted": True},
            ("PATCH", "/vitalai/flows/health-alerts/test-prefix-health/7/acknowledge"): {
                "accepted": True,
                "current_status": "acknowledged",
            },
            ("PATCH", "/vitalai/flows/health-alerts/test-prefix-health/7/resolve"): {
                "accepted": True,
                "current_status": "resolved",
            },
            ("GET", "/vitalai/flows/health-alerts/test-prefix-health"): {
                "accepted": True,
                "health_alert_snapshot": {
                    "alert_count": 1,
                    "recent_risk_levels": ["high"],
                    "entries": [{"status": "resolved"}],
                },
            },
            ("POST", "/vitalai/flows/daily-life-checkin"): {"accepted": True},
            ("GET", "/vitalai/flows/daily-life-checkins/test-prefix-daily"): {
                "accepted": True,
                "daily_life_snapshot": {"checkin_count": 1, "recent_needs": ["meal_support"]},
            },
            ("POST", "/vitalai/flows/mental-care-checkin"): {"accepted": True},
            ("GET", "/vitalai/flows/mental-care-checkins/test-prefix-mental"): {
                "accepted": True,
                "mental_care_snapshot": {
                    "checkin_count": 1,
                    "recent_mood_signals": ["calm"],
                    "recent_support_needs": ["companionship"],
                },
            },
        }

        with patch(
            "scripts.manual_smoke_typed_flow_http._request_json",
            side_effect=lambda base_url, path, **kwargs: (
                {"accepted": True, "health_alert_entry": {"alert_id": 7}}
                if path == "/vitalai/flows/health-alert"
                else responses[(kwargs.get("method", "GET").upper(), path)]
            ),
        ):
            report = run_typed_flow_http_smoke(user_prefix="test-prefix")

        self.assertFalse(report["ok"])
        self.assertFalse(report["flows"]["profile_memory"]["ok"])
        self.assertTrue(report["flows"]["health"]["ok"])

    def test_format_text_report_summarizes_typed_flows(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "health_endpoint": {"status": "ok", "module": "VitalAI"},
            "flows": {
                "profile_memory": {
                    "ok": True,
                    "user_id": "typed-profile",
                    "read": {"profile_snapshot": {"memory_count": 1, "memory_keys": ["favorite_drink"]}},
                },
                "health": {
                    "ok": True,
                    "user_id": "typed-health",
                    "read": {
                        "health_alert_snapshot": {
                            "alert_count": 1,
                            "recent_risk_levels": ["high"],
                            "entries": [{"status": "resolved"}],
                        }
                    },
                },
                "daily_life": {
                    "ok": True,
                    "user_id": "typed-daily",
                    "read": {"daily_life_snapshot": {"checkin_count": 1, "recent_needs": ["meal_support"]}},
                },
                "mental_care": {
                    "ok": True,
                    "user_id": "typed-mental",
                    "read": {
                        "mental_care_snapshot": {
                            "checkin_count": 1,
                            "recent_mood_signals": ["calm"],
                            "recent_support_needs": ["companionship"],
                        }
                    },
                },
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI typed-flow HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("health_endpoint: OK module=VitalAI", text)
        self.assertIn("profile_memory: OK user_id=typed-profile memory_count=1", text)
        self.assertIn("health: OK user_id=typed-health alert_count=1 recent_risk_levels=high status=resolved", text)
        self.assertIn("daily_life: OK user_id=typed-daily checkin_count=1", text)
        self.assertIn("mental_care: OK user_id=typed-mental checkin_count=1", text)

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_typed_flow_http.py",
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
