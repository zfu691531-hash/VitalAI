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
        self.assertEqual(200, query_response.status_code)
        query_body = query_response.json()
        self.assertTrue(query_body["accepted"])
        self.assertEqual("PROFILE_MEMORY_QUERY", query_body["routed_event_type"])
        self.assertEqual(1, query_body["memory_updates"]["profile_snapshot"]["memory_count"])
        self.assertEqual("jasmine_tea", query_body["memory_updates"]["profile_snapshot"]["entries"][0]["memory_value"])

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


if __name__ == "__main__":
    unittest.main()
