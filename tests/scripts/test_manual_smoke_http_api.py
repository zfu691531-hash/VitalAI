"""Tests for the running-server HTTP smoke script."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import ANY
from unittest.mock import patch

from scripts.manual_smoke_http_api import DEFAULT_BASE_URL, format_text_report, run_http_smoke


class ManualSmokeHttpApiTests(unittest.TestCase):
    def test_run_http_smoke_checks_health_write_read_and_interaction(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            (
                "POST",
                "/vitalai/flows/profile-memory",
            ): {
                "accepted": True,
                "event_type": "PROFILE_MEMORY_UPDATE",
                "stored_entry": {"memory_key": "favorite_drink"},
            },
            (
                "GET",
                "/vitalai/flows/profile-memory/test-user",
            ): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1, "memory_keys": ["favorite_drink"]},
            },
            ("POST", "/vitalai/interactions"): {
                "accepted": True,
                "routed_event_type": "PROFILE_MEMORY_UPDATE",
                "intent": {"primary_intent": "profile_memory_update"},
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
            self.assertEqual("http://127.0.0.1:8124", base_url)
            self.assertEqual(3.0, timeout_seconds)
            self.assertIn(type(query), {dict, type(None)})
            if payload is not None:
                self.assertIsInstance(payload, dict)
            return responses[(method.upper(), path)]

        with patch("scripts.manual_smoke_http_api._request_json", side_effect=fake_request_json):
            report = run_http_smoke(base_url=DEFAULT_BASE_URL, user_id="test-user", timeout_seconds=3.0)

        self.assertTrue(report["ok"])
        self.assertEqual("test-user", report["user_id"])
        self.assertEqual("ok", report["health"]["status"])
        self.assertTrue(report["profile_memory_write"]["accepted"])
        self.assertEqual(1, report["profile_memory_read"]["profile_snapshot"]["memory_count"])
        self.assertEqual(
            "profile_memory_update",
            report["interaction"]["intent"]["primary_intent"],
        )

    def test_format_text_report_summarizes_key_http_checks(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "health": {"status": "ok", "module": "VitalAI"},
            "profile_memory_write": {
                "accepted": True,
                "event_type": "PROFILE_MEMORY_UPDATE",
                "stored_entry": {"memory_key": "favorite_drink"},
            },
            "profile_memory_read": {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1, "memory_keys": ["favorite_drink"]},
            },
            "interaction": {
                "accepted": True,
                "routed_event_type": "PROFILE_MEMORY_UPDATE",
                "intent": {"primary_intent": "profile_memory_update"},
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("health: OK module=VitalAI", text)
        self.assertIn("profile_memory_write: OK event_type=PROFILE_MEMORY_UPDATE", text)
        self.assertIn("profile_memory_read: OK memory_count=1 memory_keys=favorite_drink", text)
        self.assertIn("interaction: OK routed_event_type=PROFILE_MEMORY_UPDATE", text)

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_http_api.py",
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

    def test_main_text_output_uses_formatter(self) -> None:
        fake_report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "health": {"status": "ok", "module": "VitalAI"},
            "profile_memory_write": {
                "accepted": True,
                "event_type": "PROFILE_MEMORY_UPDATE",
                "stored_entry": {"memory_key": "favorite_drink"},
            },
            "profile_memory_read": {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1, "memory_keys": ["favorite_drink"]},
            },
            "interaction": {
                "accepted": True,
                "routed_event_type": "PROFILE_MEMORY_UPDATE",
                "intent": {"primary_intent": "profile_memory_update"},
            },
        }

        with patch("scripts.manual_smoke_http_api.run_http_smoke", return_value=fake_report), patch(
            "scripts.manual_smoke_http_api.sys.argv",
            ["manual_smoke_http_api.py", "--output", "text"],
        ), patch("builtins.print") as print_mock:
            from scripts.manual_smoke_http_api import main

            exit_code = main()

        self.assertEqual(0, exit_code)
        print_mock.assert_called_once_with(ANY)
        rendered = print_mock.call_args.args[0]
        self.assertIn("VitalAI HTTP smoke: OK", rendered)


if __name__ == "__main__":
    unittest.main()
