"""Tests for the backend-only user interaction API."""

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


class UserInteractionRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    @staticmethod
    def build_test_client() -> TestClient:
        app = FastAPI(title="VitalAI Interaction Test App")
        init_http_interfaces(app)
        return TestClient(app)

    def test_interaction_route_updates_and_queries_profile_memory(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-interaction-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                update_response = client.post(
                    "/vitalai/interactions",
                    json={
                        "user_id": "elder-1801",
                        "channel": "manual",
                        "message": "I like jasmine tea.",
                        "event_type": "profile_memory_update",
                        "trace_id": "trace-interaction-route-write",
                        "context": {
                            "memory_key": "favorite_drink",
                            "memory_value": "jasmine_tea",
                        },
                    },
                )
                query_response = client.post(
                    "/vitalai/interactions",
                    json={
                        "user_id": "elder-1801",
                        "channel": "manual",
                        "message": "What do you remember?",
                        "event_type": "profile_memory_query",
                        "trace_id": "trace-interaction-route-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, update_response.status_code)
        update_body = update_response.json()
        self.assertTrue(update_body["accepted"])
        self.assertEqual("PROFILE_MEMORY_UPDATE", update_body["routed_event_type"])
        self.assertEqual("elder-1801:manual", update_body["session"]["session_id"])
        self.assertEqual("jasmine_tea", update_body["memory_updates"]["stored_entry"]["memory_value"])
        self.assertEqual("profile-memory-domain-agent", update_body["agent_handoffs"][1]["agent_id"])
        self.assertEqual("store_profile_memory", update_body["agent_cycles"][0]["decision"]["decision_type"])
        self.assertEqual(200, query_response.status_code)
        query_body = query_response.json()
        self.assertTrue(query_body["accepted"])
        self.assertEqual("PROFILE_MEMORY_QUERY", query_body["routed_event_type"])
        self.assertEqual(1, query_body["memory_updates"]["profile_snapshot"]["memory_count"])
        self.assertEqual("jasmine_tea", query_body["memory_updates"]["profile_snapshot"]["entries"][0]["memory_value"])
        self.assertEqual("profile-memory-domain-agent", query_body["agent_handoffs"][1]["agent_id"])
        self.assertEqual("load_profile_memory", query_body["agent_cycles"][0]["decision"]["decision_type"])

    def test_interaction_route_returns_unified_health_response(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1802",
                "channel": "manual",
                "message": "fall detected",
                "event_type": "health_alert",
                "trace_id": "trace-interaction-route-health",
                "context": {"risk_level": "critical"},
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("HEALTH_ALERT", body["routed_event_type"])
        self.assertEqual("dispatch_followup", body["response"])
        self.assertGreaterEqual(len(body["runtime_signals"]), 1)
        self.assertEqual("review_health_alert", body["actions"][0]["type"])
        self.assertEqual("immediate_review", body["actions"][0]["priority"])
        self.assertEqual("health-domain-agent", body["agent_handoffs"][1]["agent_id"])
        self.assertEqual("raise_health_alert", body["agent_cycles"][0]["decision"]["decision_type"])
        self.assertEqual("critical", body["agent_cycles"][0]["decision"]["payload"]["risk_assessment"]["level"])
        self.assertEqual("raised", body["agent_cycles"][0]["execution"]["payload"]["status"])

    def test_interaction_route_recognizes_intent_without_event_type(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1805",
                "channel": "manual",
                "message": "我刚刚摔倒了，现在头晕",
                "trace_id": "trace-interaction-route-intent",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("HEALTH_ALERT", body["routed_event_type"])
        self.assertEqual("health_alert", body["intent"]["primary_intent"])
        self.assertEqual("rule_based", body["intent"]["source"])
        self.assertEqual("critical", body["agent_cycles"][0]["decision"]["payload"]["risk_assessment"]["level"])
        self.assertIn(
            "fall_signal",
            body["agent_cycles"][0]["decision"]["payload"]["risk_assessment"]["signal_tags"],
        )
        self.assertEqual("immediate_review", body["actions"][0]["priority"])

    def test_interaction_route_exposes_input_preprocessing_metadata(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1807",
                "channel": "manual",
                "message": "  我刚刚   摔倒了，\n现在头晕  ",
                "trace_id": "trace-interaction-route-preprocess",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("HEALTH_ALERT", body["routed_event_type"])
        self.assertEqual("我刚刚 摔倒了， 现在头晕", body["preprocessing"]["normalized_message"])
        self.assertEqual("  我刚刚   摔倒了，\n现在头晕  ", body["preprocessing"]["original_message"])
        self.assertTrue(body["preprocessing"]["changed"])

    def test_interaction_route_requests_clarification_without_event_type(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1806",
                "channel": "manual",
                "message": "你好",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["accepted"])
        self.assertEqual("clarification_needed", body["error"])
        self.assertTrue(body["intent"]["requires_clarification"])
        self.assertEqual("intent-recognition-agent", body["agent_handoffs"][1]["agent_id"])

    def test_interaction_route_returns_unsupported_event_result(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1803",
                "channel": "manual",
                "message": "hello",
                "event_type": "unknown_event",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["accepted"])
        self.assertEqual("unsupported_event_type", body["error"])
        self.assertIsNone(body["routed_event_type"])
        self.assertIn("profile_memory_update", body["error_details"]["supported_event_types"])

    def test_interaction_route_returns_unified_invalid_request_response(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "event_type": "health_alert",
                "channel": "manual",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["accepted"])
        self.assertEqual("invalid_request", body["error"])
        self.assertIn({"field": "user_id", "code": "required"}, body["error_details"]["issues"])
        self.assertIn({"field": "message", "code": "required"}, body["error_details"]["issues"])

    def test_interaction_route_returns_unified_invalid_context_response(self) -> None:
        client = self.build_test_client()

        response = client.post(
            "/vitalai/interactions",
            json={
                "user_id": "elder-1804",
                "channel": "manual",
                "message": "remember this",
                "event_type": "profile_memory_update",
                "context": "not-an-object",
            },
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertFalse(body["accepted"])
        self.assertEqual("invalid_request", body["error"])
        self.assertIn({"field": "context", "code": "must_be_object"}, body["error_details"]["issues"])

    def test_user_overview_route_aggregates_existing_domain_snapshots(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-overview-route-{uuid4().hex}"
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
                        "source_agent": "overview-test",
                        "user_id": "elder-1810",
                        "memory_key": "favorite_drink",
                        "memory_value": "jasmine_tea",
                        "trace_id": "trace-overview-profile",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1810",
                        "risk_level": "high",
                        "trace_id": "trace-overview-health",
                    },
                )
                client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1810",
                        "need": "meal_support",
                        "urgency": "normal",
                        "trace_id": "trace-overview-daily",
                    },
                )
                client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1810",
                        "mood_signal": "calm",
                        "support_need": "emotional_checkin",
                        "trace_id": "trace-overview-mental",
                    },
                )
                response = client.get("/vitalai/users/elder-1810/overview")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-1810", body["user_id"])
        self.assertEqual(3, body["history_limit"])
        self.assertEqual(body["latest_activity_at"], body["recent_activity"][0]["occurred_at"])
        self.assertEqual(4, len(body["recent_activity"]))
        self.assertEqual(
            {"profile_memory", "health", "daily_life", "mental_care"},
            {item["domain"] for item in body["recent_activity"]},
        )
        self.assertEqual("1 attention item(s) for elder-1810.", body["attention_summary"])
        self.assertEqual(1, len(body["attention_items"]))
        self.assertEqual("health", body["attention_items"][0]["domain"])
        self.assertEqual("high", body["attention_items"][0]["severity"])
        self.assertEqual(1, body["overview"]["profile_memory"]["memory_count"])
        self.assertEqual("jasmine_tea", body["overview"]["profile_memory"]["entries"][0]["memory_value"])
        self.assertEqual(1, body["overview"]["health"]["alert_count"])
        self.assertEqual("high", body["overview"]["health"]["entries"][0]["risk_level"])
        self.assertEqual(1, body["overview"]["daily_life"]["checkin_count"])
        self.assertEqual("meal_support", body["overview"]["daily_life"]["entries"][0]["need"])
        self.assertEqual(1, body["overview"]["mental_care"]["checkin_count"])
        self.assertEqual("calm", body["overview"]["mental_care"]["entries"][0]["mood_signal"])

    def test_user_overview_route_respects_history_limit_and_memory_key(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-overview-limit-route-{uuid4().hex}"
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
                        "source_agent": "overview-test",
                        "user_id": "elder-1811",
                        "memory_key": "favorite_drink",
                        "memory_value": "green_tea",
                        "trace_id": "trace-overview-filter-memory-1",
                    },
                )
                client.post(
                    "/vitalai/flows/profile-memory",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1811",
                        "memory_key": "favorite_color",
                        "memory_value": "blue",
                        "trace_id": "trace-overview-filter-memory-2",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1811",
                        "risk_level": "high",
                        "trace_id": "trace-overview-filter-health-1",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1811",
                        "risk_level": "critical",
                        "trace_id": "trace-overview-filter-health-2",
                    },
                )
                response = client.get(
                    "/vitalai/users/elder-1811/overview",
                    params={"history_limit": 1, "memory_key": "favorite_drink"},
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(1, body["history_limit"])
        self.assertEqual(2, len(body["recent_activity"]))
        self.assertEqual("health", body["recent_activity"][0]["domain"])
        self.assertEqual("profile_memory", body["recent_activity"][1]["domain"])
        self.assertEqual("1 attention item(s) for elder-1811.", body["attention_summary"])
        self.assertEqual(1, len(body["attention_items"]))
        self.assertEqual("health", body["attention_items"][0]["domain"])
        self.assertEqual(1, body["overview"]["profile_memory"]["memory_count"])
        self.assertEqual(["favorite_drink"], body["overview"]["profile_memory"]["memory_keys"])
        self.assertEqual(1, body["overview"]["health"]["alert_count"])
        self.assertEqual("critical", body["overview"]["health"]["entries"][0]["risk_level"])

    def test_user_report_preview_route_runs_reporting_tool_and_privacy_chain(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-report-preview-route-{uuid4().hex}"
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
                        "source_agent": "report-preview-test",
                        "user_id": "elder-1813",
                        "memory_key": "favorite_drink",
                        "memory_value": "jasmine_tea",
                        "trace_id": "trace-report-preview-profile",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "report-preview-test",
                        "user_id": "elder-1813",
                        "risk_level": "high",
                        "trace_id": "trace-report-preview-health",
                    },
                )
                client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "report-preview-test",
                        "user_id": "elder-1813",
                        "need": "meal_support",
                        "urgency": "normal",
                        "trace_id": "trace-report-preview-daily",
                    },
                )
                response = client.get(
                    "/vitalai/users/elder-1813/report-preview",
                    params={"history_limit": 2},
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("intelligent-reporting-agent", body["agent_id"])
        self.assertEqual("read_only_report_preview", body["execution_mode"])
        self.assertEqual("elder-1813 overview report", body["preview"]["title"])
        self.assertIn("attention=", body["preview"]["body"])
        self.assertEqual("REPORT_REQUEST", body["envelope"]["msg_type"])
        self.assertFalse(body["envelope"]["payload"]["dry_run"])
        self.assertEqual("tool-agent", body["preview"]["source_lookup"]["collaborator_agent_id"])
        self.assertEqual("user_overview_lookup", body["preview"]["source_lookup"]["tool_name"])
        self.assertEqual("tool-agent", body["preview"]["source_lookup"]["cycle"]["agent_id"])
        self.assertTrue(body["preview"]["source_lookup"]["accepted"])
        self.assertEqual(
            "tool-agent",
            body["cycle"]["decision"]["payload"]["overview_lookup_agent_id"],
        )
        self.assertEqual(
            "privacy-guardian-agent",
            body["preview"]["security_review"]["reviewer_agent_id"],
        )
        self.assertEqual(
            "privacy-guardian-agent",
            body["cycle"]["execution"]["payload"]["security_review_agent_id"],
        )

    def test_user_overview_route_collects_attention_items_from_multiple_domains(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-overview-attention-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            env = {
                "VITALAI_HEALTH_DB_PATH": str(temp_dir / "health.sqlite3"),
                "VITALAI_DAILY_LIFE_DB_PATH": str(temp_dir / "daily-life.sqlite3"),
                "VITALAI_MENTAL_CARE_DB_PATH": str(temp_dir / "mental-care.sqlite3"),
                "VITALAI_PROFILE_MEMORY_DB_PATH": str(temp_dir / "profile-memory.sqlite3"),
            }
            with patch.dict("os.environ", env, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1812",
                        "risk_level": "critical",
                        "trace_id": "trace-overview-attention-health",
                    },
                )
                client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1812",
                        "need": "mobility_support",
                        "urgency": "high",
                        "trace_id": "trace-overview-attention-daily",
                    },
                )
                client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "overview-test",
                        "user_id": "elder-1812",
                        "mood_signal": "distressed",
                        "support_need": "emotional_checkin",
                        "trace_id": "trace-overview-attention-mental",
                    },
                )
                response = client.get("/vitalai/users/elder-1812/overview")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(3, len(body["attention_items"]))
        self.assertEqual(
            {"health", "daily_life", "mental_care"},
            {item["domain"] for item in body["attention_items"]},
        )


if __name__ == "__main__":
    unittest.main()
