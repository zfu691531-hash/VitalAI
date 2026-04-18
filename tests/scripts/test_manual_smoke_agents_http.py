"""Tests for the running-server agent registry HTTP smoke script."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.manual_smoke_agents_http import (
    DEFAULT_BASE_URL,
    format_text_report,
    run_agents_http_smoke,
)


class ManualSmokeAgentsHttpTests(unittest.TestCase):
    def test_run_agents_http_smoke_checks_registry_and_agent_previews(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("GET", "/vitalai/agents"): {
                "count": 7,
                "agents": [
                    {"agent_id": "health-domain-agent"},
                    {"agent_id": "daily-life-domain-agent"},
                    {"agent_id": "mental-care-domain-agent"},
                    {"agent_id": "profile-memory-domain-agent"},
                    {"agent_id": "intelligent-reporting-agent"},
                    {"agent_id": "tool-agent"},
                    {"agent_id": "privacy-guardian-agent"},
                ],
            },
            ("GET", "/vitalai/agents/health-domain-agent"): {
                "agent": {"agent_id": "health-domain-agent", "layer": "domain"},
            },
            ("POST", "/vitalai/agents/health-domain-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "envelope": {"to_agent": "health-domain-agent"},
                    "preview": {"health_alert_entry": {"status": "raised"}},
                }
            },
            ("POST", "/vitalai/agents/tool-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "execution_mode": "internal_tool_call",
                    "preview": {
                        "tool_name": "user_overview_lookup",
                        "executed": True,
                        "external_call_executed": False,
                        "result": {"user_id": "agent-user"},
                    },
                }
            },
            ("POST", "/vitalai/agents/privacy-guardian-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "action": "REDACT",
                        "highest_severity": "WARNING",
                        "sanitized_payload": {"api_key": "[REDACTED]"},
                    },
                }
            },
            ("POST", "/vitalai/flows/profile-memory"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1},
            },
            ("POST", "/vitalai/flows/health-alert"): {
                "accepted": True,
                "health_alert_entry": {"risk_level": "high", "status": "raised"},
            },
            ("POST", "/vitalai/agents/intelligent-reporting-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "title": "agent-user overview report",
                        "body": "latest_activity_at=...; attention=1 item; recent_domains=health",
                        "source_lookup": {
                            "collaborator_agent_id": "tool-agent",
                            "tool_name": "user_overview_lookup",
                        },
                        "security_review": {
                            "reviewer_agent_id": "privacy-guardian-agent",
                            "action": "ALLOW",
                        },
                    },
                }
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

        with patch("scripts.manual_smoke_agents_http._request_json", side_effect=fake_request_json):
            report = run_agents_http_smoke(
                base_url=DEFAULT_BASE_URL,
                user_id="agent-user",
                timeout_seconds=4.0,
            )

        self.assertTrue(report["ok"])
        self.assertTrue(report["seeded"]["profile_memory"]["ok"])
        self.assertTrue(report["seeded"]["health"]["ok"])
        self.assertEqual(7, report["registry"]["count"])

    def test_run_agents_http_smoke_marks_failed_registry(self) -> None:
        responses = {
            ("GET", "/vitalai/health"): {"status": "ok", "module": "VitalAI"},
            ("GET", "/vitalai/agents"): {"count": 1, "agents": [{"agent_id": "tool-agent"}]},
            ("GET", "/vitalai/agents/health-domain-agent"): {
                "agent": {"agent_id": "health-domain-agent", "layer": "domain"},
            },
            ("POST", "/vitalai/agents/health-domain-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "envelope": {"to_agent": "health-domain-agent"},
                    "preview": {"health_alert_entry": {"status": "raised"}},
                }
            },
            ("POST", "/vitalai/agents/tool-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "execution_mode": "internal_tool_call",
                    "preview": {
                        "tool_name": "user_overview_lookup",
                        "executed": True,
                        "external_call_executed": False,
                        "result": {"user_id": "elder-agent-http-smoke"},
                    },
                }
            },
            ("POST", "/vitalai/agents/privacy-guardian-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "action": "REDACT",
                        "highest_severity": "WARNING",
                        "sanitized_payload": {"api_key": "[REDACTED]"},
                    },
                }
            },
            ("POST", "/vitalai/flows/profile-memory"): {
                "accepted": True,
                "profile_snapshot": {"memory_count": 1},
            },
            ("POST", "/vitalai/flows/health-alert"): {
                "accepted": True,
                "health_alert_entry": {"risk_level": "high", "status": "raised"},
            },
            ("POST", "/vitalai/agents/intelligent-reporting-agent/dry-run"): {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "title": "elder-agent-http-smoke overview report",
                        "body": "latest_activity_at=...; attention=1 item; recent_domains=health",
                        "source_lookup": {
                            "collaborator_agent_id": "tool-agent",
                            "tool_name": "user_overview_lookup",
                        },
                        "security_review": {
                            "reviewer_agent_id": "privacy-guardian-agent",
                            "action": "ALLOW",
                        },
                    },
                }
            },
        }

        with patch(
            "scripts.manual_smoke_agents_http._request_json",
            side_effect=lambda base_url, path, **kwargs: responses[(kwargs.get("method", "GET").upper(), path)],
        ):
            report = run_agents_http_smoke()

        self.assertFalse(report["ok"])

    def test_format_text_report_summarizes_agent_checks(self) -> None:
        report = {
            "ok": True,
            "base_url": DEFAULT_BASE_URL,
            "user_id": "agent-user",
            "health_endpoint": {"status": "ok", "module": "VitalAI"},
            "registry": {
                "count": 7,
                "agents": [
                    {"agent_id": "health-domain-agent"},
                    {"agent_id": "daily-life-domain-agent"},
                    {"agent_id": "mental-care-domain-agent"},
                    {"agent_id": "profile-memory-domain-agent"},
                    {"agent_id": "intelligent-reporting-agent"},
                    {"agent_id": "tool-agent"},
                    {"agent_id": "privacy-guardian-agent"},
                ],
            },
            "detail": {"agent": {"agent_id": "health-domain-agent", "layer": "domain"}},
            "domain_dry_run": {
                "dry_run": {
                    "accepted": True,
                    "envelope": {"to_agent": "health-domain-agent"},
                    "preview": {"health_alert_entry": {"status": "raised"}},
                }
            },
            "tool_dry_run": {
                "dry_run": {
                    "accepted": True,
                    "execution_mode": "internal_tool_call",
                    "preview": {
                        "tool_name": "user_overview_lookup",
                        "executed": True,
                        "external_call_executed": False,
                        "result": {"user_id": "agent-user"},
                    },
                }
            },
            "privacy_dry_run": {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "action": "REDACT",
                        "highest_severity": "WARNING",
                        "sanitized_payload": {"api_key": "[REDACTED]"},
                    },
                }
            },
            "seeded": {
                "profile_memory": {"ok": True, "response": {}},
                "health": {"ok": True, "response": {}},
            },
            "reporting_dry_run": {
                "dry_run": {
                    "accepted": True,
                    "preview": {
                        "title": "agent-user overview report",
                        "body": "latest_activity_at=...; attention=1 item; recent_domains=health",
                        "source_lookup": {
                            "collaborator_agent_id": "tool-agent",
                            "tool_name": "user_overview_lookup",
                        },
                        "security_review": {
                            "reviewer_agent_id": "privacy-guardian-agent",
                            "action": "ALLOW",
                        },
                    },
                }
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI agents HTTP smoke: OK", text)
        self.assertIn(f"base_url: {DEFAULT_BASE_URL}", text)
        self.assertIn("agent_registry: OK count=7", text)
        self.assertIn("agent_detail: OK agent_id=health-domain-agent", text)
        self.assertIn("health_domain_dry_run: OK", text)
        self.assertIn("tool_dry_run: OK tool=user_overview_lookup mode=internal_tool_call", text)
        self.assertIn("privacy_dry_run: OK action=REDACT", text)
        self.assertIn(
            "reporting_dry_run: OK title=agent-user overview report lookup_agent=tool-agent privacy_action=ALLOW",
            text,
        )

    def test_cli_returns_error_when_server_is_unreachable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/manual_smoke_agents_http.py",
                "--base-url",
                "http://127.0.0.1:65530",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("Could not reach VitalAI API", completed.stderr)
