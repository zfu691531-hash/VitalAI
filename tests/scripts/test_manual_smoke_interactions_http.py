"""Tests for the running-server interactions HTTP smoke script."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.manual_smoke_interactions_http import DEFAULT_BASE_URL, format_text_report, run_interactions_http_smoke


class ManualSmokeInteractionsHttpTests(unittest.TestCase):
    def test_run_interactions_http_smoke_checks_high_value_cases(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            "trace-interactions-http-health": {
                "accepted": True,
                "routed_event_type": "HEALTH_ALERT",
                "intent": {"primary_intent": "health_alert"},
            },
            "trace-interactions-http-profile": {
                "accepted": True,
                "routed_event_type": "PROFILE_MEMORY_UPDATE",
                "intent": {"primary_intent": "profile_memory_update"},
                "memory_updates": {"stored_entry": {"memory_key": "general_note"}},
            },
            "trace-interactions-http-clarification": {
                "accepted": False,
                "error": "clarification_needed",
                "routed_event_type": None,
                "intent": {"requires_clarification": True},
            },
            "trace-interactions-http-decomposition": {
                "accepted": False,
                "error": "decomposition_needed",
                "routed_event_type": None,
                "error_details": {
                    "decomposition": {"status": "pending_second_layer"},
                    "decomposition_guard": {"status": "hold_for_second_layer"},
                },
            },
            "invalid-request": {
                "accepted": False,
                "error": "invalid_request",
                "error_details": {
                    "issues": [
                        {"field": "user_id", "code": "required"},
                        {"field": "message", "code": "required"},
                    ]
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
            self.assertIn(type(query), {dict, type(None)})
            if path == "/vitalai/health":
                return responses[(method.upper(), path)]
            self.assertEqual("POST", method.upper())
            self.assertIsInstance(payload, dict)
            trace_id = payload.get("trace_id", "invalid-request")
            return responses[str(trace_id)]

        with patch("scripts.manual_smoke_interactions_http._request_json", side_effect=fake_request_json):
            report = run_interactions_http_smoke(
                base_url=DEFAULT_BASE_URL,
                user_prefix="test-interactions",
                timeout_seconds=4.0,
            )

        self.assertTrue(report["ok"])
        cases = report["cases"]
        self.assertTrue(cases["health_route"]["ok"])
        self.assertTrue(cases["profile_memory_route"]["ok"])
        self.assertTrue(cases["clarification_case"]["ok"])
        self.assertTrue(cases["decomposition_case"]["ok"])
        self.assertTrue(cases["invalid_request_case"]["ok"])

    def test_run_interactions_http_smoke_marks_failed_case(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            "trace-interactions-http-health": {
                "accepted": True,
                "routed_event_type": "HEALTH_ALERT",
                "intent": {"primary_intent": "health_alert"},
            },
            "trace-interactions-http-profile": {
                "accepted": True,
                "routed_event_type": "PROFILE_MEMORY_UPDATE",
                "intent": {"primary_intent": "profile_memory_update"},
                "memory_updates": {"stored_entry": {"memory_key": "favorite_drink"}},
            },
            "trace-interactions-http-clarification": {
                "accepted": False,
                "error": "clarification_needed",
                "routed_event_type": None,
                "intent": {"requires_clarification": True},
            },
            "trace-interactions-http-decomposition": {
                "accepted": False,
                "error": "decomposition_needed",
                "routed_event_type": None,
                "error_details": {
                    "decomposition": {"status": "pending_second_layer"},
                    "decomposition_guard": {"status": "hold_for_second_layer"},
                },
            },
            "invalid-request": {
                "accepted": False,
                "error": "invalid_request",
                "error_details": {
                    "issues": [
                        {"field": "user_id", "code": "required"},
                        {"field": "message", "code": "required"},
                    ]
                },
            },
        }

        with patch(
            "scripts.manual_smoke_interactions_http._request_json",
            side_effect=lambda base_url, path, **kwargs: (
                responses[("GET", path)]
                if path == "/vitalai/health"
                else responses[str(kwargs["payload"].get("trace_id", "invalid-request"))]
            ),
        ):
            report = run_interactions_http_smoke(user_prefix="test-interactions")

        self.assertFalse(report["ok"])
        self.assertFalse(report["cases"]["profile_memory_route"]["ok"])
        self.assertTrue(report["cases"]["health_route"]["ok"])

    def test_format_text_report_summarizes_interaction_cases(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "health_endpoint": {"status": "ok", "module": "VitalAI"},
            "cases": {
                "health_route": {
                    "ok": True,
                    "user_id": "interaction-health",
                    "response": {
                        "routed_event_type": "HEALTH_ALERT",
                        "intent": {"primary_intent": "health_alert"},
                    },
                },
                "profile_memory_route": {
                    "ok": True,
                    "user_id": "interaction-memory",
                    "response": {
                        "routed_event_type": "PROFILE_MEMORY_UPDATE",
                        "memory_updates": {"stored_entry": {"memory_key": "general_note"}},
                    },
                },
                "clarification_case": {
                    "ok": True,
                    "user_id": "interaction-clarify",
                    "response": {
                        "error": "clarification_needed",
                        "intent": {"requires_clarification": True},
                    },
                },
                "decomposition_case": {
                    "ok": True,
                    "user_id": "interaction-decompose",
                    "response": {
                        "error": "decomposition_needed",
                        "error_details": {"decomposition_guard": {"status": "hold_for_second_layer"}},
                    },
                },
                "invalid_request_case": {
                    "ok": True,
                    "response": {
                        "error": "invalid_request",
                        "error_details": {
                            "issues": [
                                {"field": "user_id", "code": "required"},
                                {"field": "message", "code": "required"},
                            ]
                        },
                    },
                },
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI interactions HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("health_endpoint: OK module=VitalAI", text)
        self.assertIn("health_route: OK user_id=interaction-health routed_event_type=HEALTH_ALERT", text)
        self.assertIn("profile_memory_route: OK user_id=interaction-memory", text)
        self.assertIn("clarification_case: OK user_id=interaction-clarify error=clarification_needed", text)
        self.assertIn("decomposition_case: OK user_id=interaction-decompose error=decomposition_needed", text)
        self.assertIn("invalid_request_case: OK error=invalid_request issue_fields=message,user_id", text)

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_interactions_http.py",
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
