"""Tests for typed application flow route adapters."""

from __future__ import annotations

import unittest
from pathlib import Path
import shutil
from uuid import uuid4
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from VitalAI.interfaces import typed_flow_support
from VitalAI.interfaces.api.app import init_http_interfaces
from VitalAI.interfaces.api.routers.typed_flows import (
    DailyLifeCheckInRequest,
    HealthAlertRequest,
    MentalCareCheckInRequest,
    ProfileMemoryUpdateRequest,
    get_profile_memory_snapshot,
    get_health_failover_drill,
    get_runtime_diagnostics,
    get_runtime_policy,
    get_runtime_policy_matrix,
    get_runtime_policy_observation,
    run_daily_life_checkin,
    run_health_alert,
    run_mental_care_checkin,
    run_profile_memory_update,
    router,
)


class TypedFlowRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    @staticmethod
    def build_test_client() -> TestClient:
        app = FastAPI(title="VitalAI Route Test App")
        init_http_interfaces(app)
        return TestClient(app)

    def test_health_alert_route_adapter_returns_expected_shape(self) -> None:
        response = run_health_alert(
            HealthAlertRequest(
                source_agent="health-api",
                trace_id="trace-api-health-1",
                user_id="elder-801",
                risk_level="critical",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("HEALTH_ALERT", response["event_type"])
        self.assertEqual("HEALTH_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(6, len(response["runtime_signals"]))
        self.assertEqual("EVENT_SUMMARY", response["runtime_signals"][0]["kind"])
        self.assertEqual("HEALTH_ALERT", response["runtime_signals"][0]["details"]["event_type"])
        self.assertEqual("SECURITY_REVIEW", response["runtime_signals"][1]["kind"])
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertEqual("TAKEOVER", response["runtime_signals"][4]["details"]["action"])
        self.assertEqual("decision-core", response["runtime_signals"][4]["details"]["target"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])

    def test_daily_life_route_adapter_returns_expected_shape(self) -> None:
        response = run_daily_life_checkin(
            DailyLifeCheckInRequest(
                source_agent="daily-api",
                trace_id="trace-api-daily-1",
                user_id="elder-802",
                need="mobility_support",
                urgency="high",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("DAILY_LIFE_CHECKIN", response["event_type"])
        self.assertEqual("DAILY_LIFE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(6, len(response["runtime_signals"]))
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])

    def test_mental_care_route_adapter_returns_expected_shape(self) -> None:
        response = run_mental_care_checkin(
            MentalCareCheckInRequest(
                source_agent="mental-api",
                trace_id="trace-api-mental-1",
                user_id="elder-803",
                mood_signal="distressed",
                support_need="emotional_checkin",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("MENTAL_CARE_CHECKIN", response["event_type"])
        self.assertEqual("MENTAL_CARE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(2, len(response["runtime_signals"]))

    def test_profile_memory_route_adapter_returns_persisted_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                response = run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-1",
                        user_id="elder-804",
                        memory_key="favorite_drink",
                        memory_value="ginger_tea",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("PROFILE_MEMORY_UPDATE", response["event_type"])
        self.assertEqual("PROFILE_MEMORY_DECISION", response["decision_type"])
        self.assertEqual("favorite_drink", response["stored_entry"]["memory_key"])
        self.assertEqual("ginger_tea", response["stored_entry"]["memory_value"])
        self.assertEqual("elder-804", response["profile_snapshot"]["user_id"])
        self.assertEqual(1, response["profile_snapshot"]["memory_count"])
        self.assertEqual("ginger_tea", response["profile_snapshot"]["entries"][0]["memory_value"])
        self.assertIsNotNone(response["feedback_report"])

    def test_profile_memory_snapshot_route_adapter_returns_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-read-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-write",
                        user_id="elder-805",
                        memory_key="favorite_music",
                        memory_value="jazz",
                    )
                )
                response = get_profile_memory_snapshot(
                    "elder-805",
                    source_agent="profile-api",
                    trace_id="trace-api-profile-read",
                )
                empty_response = get_profile_memory_snapshot("elder-empty")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-805", response["user_id"])
        self.assertEqual("elder-805", response["profile_snapshot"]["user_id"])
        self.assertEqual(1, response["profile_snapshot"]["memory_count"])
        self.assertEqual("favorite_music", response["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual("jazz", response["profile_snapshot"]["entries"][0]["memory_value"])
        self.assertTrue(empty_response["accepted"])
        self.assertEqual("elder-empty", empty_response["profile_snapshot"]["user_id"])
        self.assertEqual(0, empty_response["profile_snapshot"]["memory_count"])

    def test_profile_memory_snapshot_http_route_reads_after_update(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-http-read-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/profile-memory",
                    json={
                        "source_agent": "profile-api",
                        "trace_id": "trace-api-profile-http-write",
                        "user_id": "elder-806",
                        "memory_key": "walking_preference",
                        "memory_value": "morning",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/profile-memory/elder-806",
                    params={
                        "source_agent": "profile-api",
                        "trace_id": "trace-api-profile-http-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-806", body["user_id"])
        self.assertEqual(1, body["profile_snapshot"]["memory_count"])
        self.assertEqual("walking_preference", body["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual("morning", body["profile_snapshot"]["entries"][0]["memory_value"])

    def test_runtime_policy_route_exposes_scheduler_policy_snapshot(self) -> None:
        response = get_runtime_policy("scheduler")

        self.assertEqual("scheduler", response["runtime_role"])
        self.assertFalse(response["reporting_enabled"])
        self.assertEqual("role_default", response["reporting_policy_source"])
        self.assertFalse(response["require_ack_override"])
        self.assertEqual(300, response["ttl_override"])
        self.assertEqual("role_default", response["ingress_policy_source"])

    def test_runtime_policy_matrix_route_exposes_all_standard_roles(self) -> None:
        response = get_runtime_policy_matrix()

        self.assertEqual({"default", "api", "scheduler", "consumer"}, set(response))
        self.assertTrue(response["api"]["reporting_enabled"])
        self.assertEqual("assembly_default", response["api"]["reporting_policy_source"])
        self.assertFalse(response["scheduler"]["reporting_enabled"])
        self.assertEqual("role_default", response["scheduler"]["reporting_policy_source"])
        self.assertFalse(response["scheduler"]["runtime_signals_enabled"])
        self.assertEqual("role_default", response["scheduler"]["runtime_signals_policy_source"])
        self.assertTrue(response["consumer"]["require_ack_override"])
        self.assertEqual(60, response["consumer"]["ttl_override"])
        self.assertEqual("role_default", response["consumer"]["ingress_policy_source"])

    def test_runtime_policy_observation_route_exposes_observability_shape(self) -> None:
        response = get_runtime_policy_observation("scheduler")

        self.assertEqual("POLICY_SNAPSHOT", response["kind"])
        self.assertEqual("INFO", response["severity"])
        self.assertEqual("application-assembly", response["source"])
        self.assertEqual("scheduler", response["attributes"]["runtime_role"])
        self.assertFalse(response["attributes"]["reporting_enabled"])
        self.assertEqual("role_default", response["attributes"]["reporting_policy_source"])
        self.assertFalse(response["attributes"]["runtime_signals_enabled"])
        self.assertEqual("role_default", response["attributes"]["runtime_signals_policy_source"])
        self.assertEqual("role_default", response["attributes"]["ingress_policy_source"])

    def test_runtime_diagnostics_route_exposes_snapshot_and_failover_signals(self) -> None:
        response = get_runtime_diagnostics("api")

        self.assertEqual("api", response["runtime_role"])
        self.assertEqual("api-runtime-snapshot", response["snapshot_id"])
        self.assertTrue(response["failover_triggered"])
        self.assertEqual("shadow", response["active_node"])
        self.assertIsNone(response["interrupt_action"])
        self.assertIsNone(response["interrupt_has_snapshot_refs"])
        self.assertEqual("ALLOW", response["latest_security_action"])
        self.assertEqual(0, response["latest_security_finding_count"])
        self.assertEqual("INFO", response["latest_security_highest_severity"])
        self.assertIsNotNone(response["latest_failover_signal_id"])
        self.assertEqual(3, len(response["runtime_signals"]))
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][0]["kind"])
        self.assertEqual("FAILOVER_TRANSITION", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["has_snapshot_refs"])
        self.assertEqual(["api-runtime-snapshot"], response["runtime_signals"][2]["details"]["snapshot_ids"])

    def test_health_failover_drill_route_exposes_controlled_failover_path(self) -> None:
        response = get_health_failover_drill("api")

        self.assertEqual("api", response["runtime_role"])
        self.assertTrue(response["failover_triggered"])
        self.assertEqual("shadow", response["active_node"])
        self.assertTrue(response["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("TAKEOVER", response["interrupt_action"])
        self.assertTrue(response["interrupt_has_snapshot_refs"])
        self.assertEqual("ALLOW", response["latest_security_action"])
        self.assertEqual(0, response["latest_security_finding_count"])
        self.assertEqual("INFO", response["latest_security_highest_severity"])
        self.assertIsNotNone(response["latest_failover_signal_id"])
        self.assertEqual(7, len(response["runtime_signals"]))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])
        self.assertEqual("FAILOVER_TRANSITION", response["runtime_signals"][6]["kind"])
        self.assertTrue(response["runtime_signals"][6]["details"]["has_snapshot_refs"])
        self.assertEqual([response["snapshot_id"]], response["runtime_signals"][6]["details"]["snapshot_ids"])

    def test_runtime_control_routes_use_post_admin_paths(self) -> None:
        route_methods = {
            route.path: route.methods
            for route in router.routes
            if hasattr(route, "methods")
        }

        self.assertEqual({"POST"}, route_methods["/admin/runtime-diagnostics/{role}"])
        self.assertEqual({"POST"}, route_methods["/admin/runtime-diagnostics/{role}/health-failover"])
        self.assertNotIn("/flows/runtime-diagnostics/{role}", route_methods)
        self.assertNotIn("/flows/runtime-diagnostics/{role}/health-failover", route_methods)

    def test_runtime_control_routes_are_blocked_by_default_in_production(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            headers = {"X-VitalAI-Admin-Token": "test-admin-token"}
            diagnostics_response = client.post("/vitalai/admin/runtime-diagnostics/api", headers=headers)
            drill_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api/health-failover",
                headers=headers,
            )

        self.assertEqual(403, diagnostics_response.status_code)
        self.assertEqual(403, drill_response.status_code)

    def test_runtime_control_routes_require_configured_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            response = client.post("/vitalai/admin/runtime-diagnostics/api")

        self.assertEqual(403, response.status_code)
        self.assertIn("Admin control token is not configured", response.json()["detail"])

    def test_runtime_control_routes_reject_missing_or_invalid_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            missing_response = client.post("/vitalai/admin/runtime-diagnostics/api")
            invalid_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "wrong-token"},
            )

        self.assertEqual(403, missing_response.status_code)
        self.assertEqual(403, invalid_response.status_code)
        self.assertEqual("Invalid admin token.", missing_response.json()["detail"])
        self.assertEqual("Invalid admin token.", invalid_response.json()["detail"])

    def test_runtime_control_routes_can_be_enabled_explicitly_in_production(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("api", response.json()["runtime_role"])

    def test_runtime_control_routes_run_with_valid_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            diagnostics_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )
            drill_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api/health-failover",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )

        self.assertEqual(200, diagnostics_response.status_code)
        self.assertEqual("api", diagnostics_response.json()["runtime_role"])
        self.assertEqual(200, drill_response.status_code)
        self.assertEqual("api", drill_response.json()["runtime_role"])


if __name__ == "__main__":
    unittest.main()
