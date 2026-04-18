"""Tests for the lightweight agent registry and dry-run HTTP adapters."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from VitalAI.interfaces import typed_flow_support
from VitalAI.interfaces.api.app import init_http_interfaces


class AgentRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    @staticmethod
    def build_test_client() -> TestClient:
        app = FastAPI(title="VitalAI Agent Route Test App")
        init_http_interfaces(app)
        return TestClient(app)

    def test_agent_registry_lists_expected_agents(self) -> None:
        client = self.build_test_client()

        response = client.get("/vitalai/agents")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual(7, body["count"])
        agent_ids = [item["agent_id"] for item in body["agents"]]
        self.assertEqual(
            [
                "health-domain-agent",
                "daily-life-domain-agent",
                "mental-care-domain-agent",
                "profile-memory-domain-agent",
                "intelligent-reporting-agent",
                "tool-agent",
                "privacy-guardian-agent",
            ],
            agent_ids,
        )

    def test_agent_detail_route_returns_tool_agent_descriptor(self) -> None:
        client = self.build_test_client()

        response = client.get("/vitalai/agents/tool-agent")

        self.assertEqual(200, response.status_code)
        agent = response.json()["agent"]
        self.assertEqual("tool-agent", agent["agent_id"])
        self.assertEqual("platform", agent["layer"])
        self.assertEqual("hybrid_tool_gateway", agent["execution_mode"])

    def test_agent_dry_run_route_executes_internal_tool_lookup(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"agent-tool-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            env = {
                "VITALAI_PROFILE_MEMORY_DB_PATH": str(temp_dir / "profile-memory.sqlite3"),
                "VITALAI_HEALTH_DB_PATH": str(temp_dir / "health.sqlite3"),
                "VITALAI_DAILY_LIFE_DB_PATH": str(temp_dir / "daily-life.sqlite3"),
                "VITALAI_MENTAL_CARE_DB_PATH": str(temp_dir / "mental-care.sqlite3"),
            }
            with patch.dict("os.environ", env, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()
                client.post(
                    "/vitalai/flows/profile-memory",
                    json={
                        "source_agent": "tool-test",
                        "trace_id": "trace-tool-profile",
                        "user_id": "elder-tool-01",
                        "memory_key": "favorite_drink",
                        "memory_value": "jasmine_tea",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "tool-test",
                        "trace_id": "trace-tool-health",
                        "user_id": "elder-tool-01",
                        "risk_level": "high",
                    },
                )
                response = client.post(
                    "/vitalai/agents/tool-agent/dry-run",
                    json={
                        "source_agent": "agent-route-test",
                        "trace_id": "trace-agent-tool-preview",
                        "tool_name": "user_overview_lookup",
                        "params": {
                            "user_id": "elder-tool-01",
                            "history_limit": 2,
                        },
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        dry_run = response.json()["dry_run"]
        self.assertTrue(dry_run["accepted"])
        self.assertEqual("internal_tool_call", dry_run["execution_mode"])
        self.assertEqual("user_overview_lookup", dry_run["preview"]["tool_name"])
        self.assertTrue(dry_run["preview"]["executed"])
        self.assertEqual("internal_read_only", dry_run["preview"]["tool_kind"])
        self.assertEqual("elder-tool-01", dry_run["preview"]["result"]["user_id"])
        self.assertGreaterEqual(len(dry_run["preview"]["result"]["recent_activity"]), 1)
        self.assertGreaterEqual(dry_run["preview"]["result"]["attention_count"], 1)
        self.assertEqual("execute_internal_tool", dry_run["cycle"]["decision"]["decision_type"])
        self.assertEqual("user_overview_lookup", dry_run["cycle"]["decision"]["payload"]["tool_name"])
        self.assertEqual("execute_user_overview_lookup", dry_run["cycle"]["execution"]["action"])

    def test_agent_dry_run_route_executes_health_domain_agent(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"agent-health-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()
                response = client.post(
                    "/vitalai/agents/health-domain-agent/dry-run",
                    json={
                        "source_agent": "agent-route-test",
                        "trace_id": "trace-agent-health-preview",
                        "user_id": "elder-agent-01",
                        "message": "dizzy and weak",
                        "context": {"risk_level": "high"},
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        dry_run = response.json()["dry_run"]
        self.assertTrue(dry_run["accepted"])
        self.assertEqual("health-domain-agent", dry_run["agent_id"])
        self.assertEqual("DOMAIN_DISPATCH", dry_run["envelope"]["msg_type"])
        self.assertEqual("health-domain-agent", dry_run["envelope"]["to_agent"])
        self.assertEqual("raised", dry_run["preview"]["health_alert_entry"]["status"])
        self.assertEqual("raise_health_alert", dry_run["cycle"]["decision"]["decision_type"])
        self.assertEqual("high", dry_run["cycle"]["decision"]["payload"]["risk_assessment"]["level"])
        self.assertEqual(
            "urgent_review",
            dry_run["cycle"]["decision"]["payload"]["action_plan"]["followup_priority"],
        )
        self.assertEqual("high", dry_run["cycle"]["execution"]["payload"]["stored_risk_level"])

    def test_agent_dry_run_route_executes_privacy_guardian_review(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/agents/privacy-guardian-agent/dry-run",
            json={
                "source_agent": "agent-route-test",
                "payload": {
                    "text": "Call me at 13812345678 or test@example.com",
                    "api_key": "sk-secret-token",
                },
            },
        )

        self.assertEqual(200, response.status_code)
        dry_run = response.json()["dry_run"]
        self.assertTrue(dry_run["accepted"])
        self.assertEqual("REDACT", dry_run["preview"]["action"])
        self.assertIn("api_key", dry_run["preview"]["sanitized_fields"])
        self.assertEqual("WARNING", dry_run["preview"]["highest_severity"])
        sanitized_payload = dry_run["preview"]["sanitized_payload"]
        self.assertEqual("[REDACTED]", sanitized_payload["api_key"])
        self.assertIn("[REDACTED]", sanitized_payload["text"])
        self.assertEqual("security_review", dry_run["cycle"]["decision"]["decision_type"])
        self.assertEqual("REDACT", dry_run["cycle"]["decision"]["payload"]["action"])
        self.assertEqual("WARNING", dry_run["cycle"]["execution"]["payload"]["highest_severity"])

    def test_agent_dry_run_route_executes_reporting_preview(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"agent-report-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            env = {
                "VITALAI_PROFILE_MEMORY_DB_PATH": str(temp_dir / "profile-memory.sqlite3"),
                "VITALAI_HEALTH_DB_PATH": str(temp_dir / "health.sqlite3"),
                "VITALAI_DAILY_LIFE_DB_PATH": str(temp_dir / "daily-life.sqlite3"),
                "VITALAI_MENTAL_CARE_DB_PATH": str(temp_dir / "mental-care.sqlite3"),
            }
            with patch.dict("os.environ", env, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                client.post(
                    "/vitalai/flows/profile-memory",
                    json={
                        "source_agent": "report-test",
                        "trace_id": "trace-report-profile",
                        "user_id": "elder-report-01",
                        "memory_key": "favorite_food",
                        "memory_value": "noodles",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "report-test",
                        "trace_id": "trace-report-health",
                        "user_id": "elder-report-01",
                        "risk_level": "high",
                    },
                )
                response = client.post(
                    "/vitalai/agents/intelligent-reporting-agent/dry-run",
                    json={
                        "source_agent": "agent-route-test",
                        "trace_id": "trace-agent-report-preview",
                        "user_id": "elder-report-01",
                        "history_limit": 3,
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        dry_run = response.json()["dry_run"]
        self.assertTrue(dry_run["accepted"])
        self.assertEqual("intelligent-reporting-agent", dry_run["agent_id"])
        self.assertEqual("REPORT_REQUEST", dry_run["envelope"]["msg_type"])
        self.assertEqual("elder-report-01 overview report", dry_run["preview"]["title"])
        self.assertIn("attention", dry_run["preview"]["body"])
        self.assertEqual(
            "tool-agent",
            dry_run["preview"]["source_lookup"]["collaborator_agent_id"],
        )
        self.assertEqual(
            "user_overview_lookup",
            dry_run["preview"]["source_lookup"]["tool_name"],
        )
        self.assertEqual(
            "tool-agent",
            dry_run["preview"]["source_lookup"]["cycle"]["agent_id"],
        )
        self.assertEqual("generate_overview_report_preview", dry_run["cycle"]["decision"]["decision_type"])
        self.assertEqual(
            "privacy-guardian-agent",
            dry_run["preview"]["security_review"]["reviewer_agent_id"],
        )
        self.assertEqual(
            "tool-agent",
            dry_run["cycle"]["decision"]["payload"]["overview_lookup_agent_id"],
        )
        self.assertEqual(
            "user_overview_lookup",
            dry_run["cycle"]["decision"]["payload"]["overview_lookup_tool_name"],
        )
        self.assertEqual(
            "privacy-guardian-agent",
            dry_run["cycle"]["decision"]["payload"]["security_review_agent_id"],
        )
        self.assertEqual(
            "tool-agent",
            dry_run["cycle"]["execution"]["payload"]["overview_lookup_agent_id"],
        )
        self.assertEqual(
            "privacy-guardian-agent",
            dry_run["cycle"]["execution"]["payload"]["security_review_agent_id"],
        )

    def test_agent_detail_route_returns_not_found_for_unknown_agent(self) -> None:
        client = self.build_test_client()

        response = client.get("/vitalai/agents/unknown-agent")

        self.assertEqual(404, response.status_code)
        detail = response.json()["detail"]
        self.assertEqual("agent_not_found", detail["error"])
        self.assertEqual("unknown-agent", detail["agent_id"])
