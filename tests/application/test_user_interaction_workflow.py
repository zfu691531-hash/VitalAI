"""Tests for the backend-only user interaction workflow."""

from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from VitalAI.application import UserInteractionCommand, build_application_assembly_from_environment_for_role


class UserInteractionWorkflowTests(unittest.TestCase):
    def test_interaction_workflow_routes_profile_memory_update_and_query(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-interaction-profile-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "profile-memory.sqlite3"
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_user_interaction_workflow()

                update_result = workflow.run(
                    UserInteractionCommand(
                        user_id="elder-1701",
                        channel="manual",
                        message="I prefer warm ginger tea.",
                        event_type="profile_memory_update",
                        trace_id="trace-interaction-profile-write",
                        context={
                            "memory_key": "favorite_drink",
                            "memory_value": "ginger_tea",
                        },
                    )
                )
                query_result = workflow.run(
                    UserInteractionCommand(
                        user_id="elder-1701",
                        channel="manual",
                        message="What do you remember about me?",
                        event_type="profile_memory_query",
                        trace_id="trace-interaction-profile-read",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(update_result.accepted)
        self.assertEqual("profile_memory_update", update_result.event_type)
        self.assertEqual("PROFILE_MEMORY_UPDATE", update_result.routed_event_type)
        self.assertEqual("profile_memory_updated", update_result.response)
        self.assertEqual(
            {"session_id": "elder-1701:manual", "user_id": "elder-1701", "channel": "manual"},
            update_result.session,
        )
        self.assertEqual("favorite_drink", update_result.memory_updates["stored_entry"]["memory_key"])
        self.assertEqual("ginger_tea", update_result.memory_updates["stored_entry"]["memory_value"])
        self.assertTrue(query_result.accepted)
        self.assertEqual("PROFILE_MEMORY_QUERY", query_result.routed_event_type)
        self.assertEqual("profile_memory_snapshot_loaded", query_result.response)
        self.assertEqual(1, query_result.memory_updates["profile_snapshot"]["memory_count"])
        self.assertEqual(
            "ginger_tea",
            query_result.memory_updates["profile_snapshot"]["entries"][0]["memory_value"],
        )

    def test_interaction_workflow_routes_health_alert(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1702",
                channel="manual",
                message="fall detected",
                event_type="health_alert",
                trace_id="trace-interaction-health",
                context={"risk_level": "critical"},
            )
        )

        self.assertTrue(result.accepted)
        self.assertEqual("HEALTH_ALERT", result.routed_event_type)
        self.assertEqual("dispatch_followup", result.response)
        self.assertGreaterEqual(len(result.runtime_signals), 1)
        self.assertEqual("review_health_alert", result.actions[0]["type"])

    def test_interaction_workflow_recognizes_health_intent_without_event_type(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1705",
                channel="manual",
                message="我刚刚摔倒了，现在有点头晕",
                trace_id="trace-interaction-health-intent",
            )
        )

        self.assertTrue(result.accepted)
        self.assertEqual("health_alert", result.event_type)
        self.assertEqual("HEALTH_ALERT", result.routed_event_type)
        self.assertEqual("health_alert", result.intent["primary_intent"])
        self.assertEqual("rule_based", result.intent["source"])

    def test_interaction_workflow_recognizes_profile_memory_update_without_event_type(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"user-interaction-intent-profile-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = temp_dir / "profile-memory.sqlite3"
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": str(db_path)}, clear=False):
                assembly = build_application_assembly_from_environment_for_role("api")
                workflow = assembly.build_user_interaction_workflow()

                result = workflow.run(
                    UserInteractionCommand(
                        user_id="elder-1706",
                        channel="manual",
                        message="帮我记住我喜欢喝姜茶",
                        trace_id="trace-interaction-profile-intent",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(result.accepted)
        self.assertEqual("profile_memory_update", result.event_type)
        self.assertEqual("PROFILE_MEMORY_UPDATE", result.routed_event_type)
        self.assertEqual("profile_memory_update", result.intent["primary_intent"])
        self.assertEqual("general_note", result.memory_updates["stored_entry"]["memory_key"])

    def test_interaction_workflow_requests_clarification_without_recognized_intent(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1707",
                channel="manual",
                message="你好",
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual("clarification_needed", result.error)
        self.assertIsNone(result.routed_event_type)
        self.assertTrue(result.intent["requires_clarification"])

    def test_interaction_workflow_requests_decomposition_for_compound_intent(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1708",
                channel="manual",
                message=(
                    "\u6211\u5fc3\u91cc\u8001\u662f\u614c\u614c\u7684\uff0c"
                    "\u90a3\u4e2a\u836f\u6211\u5230\u5e95\u8981\u4e0d\u8981\u5929\u5929\u5403\u554a\u3002"
                ),
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual("decomposition_needed", result.error)
        self.assertIsNone(result.routed_event_type)
        self.assertTrue(result.intent["requires_decomposition"])
        self.assertEqual("needs_decomposition_detector", result.intent["source"])
        self.assertEqual(
            "pending_second_layer",
            result.error_details["decomposition"]["status"],
        )
        self.assertFalse(result.error_details["decomposition"]["ready_for_routing"])
        self.assertEqual(
            "hold_for_second_layer_decomposition",
            result.error_details["decomposition"]["routing_decision"],
        )

    def test_interaction_workflow_returns_unsupported_event_result(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1703",
                channel="manual",
                message="hello",
                event_type="unknown_event",
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual("unsupported_event_type", result.error)
        self.assertIsNone(result.routed_event_type)
        self.assertIn("profile_memory_query", result.error_details["supported_event_types"])

    def test_interaction_workflow_rejects_missing_required_fields(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="",
                channel="manual",
                message="",
                event_type="health_alert",
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual("invalid_request", result.error)
        self.assertEqual("Invalid user interaction request", result.response)
        self.assertIn({"field": "user_id", "code": "required"}, result.error_details["issues"])
        self.assertIn({"field": "message", "code": "required"}, result.error_details["issues"])

    def test_interaction_workflow_rejects_invalid_context_for_profile_memory_update(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1704",
                channel="manual",
                message="remember this",
                event_type="remember",
                context={"memory_key": "favorite_drink"},
            )
        )

        self.assertFalse(result.accepted)
        self.assertEqual("profile_memory_update", result.event_type)
        self.assertEqual("invalid_context", result.error)
        self.assertEqual(["memory_value"], result.error_details["missing_fields"])


if __name__ == "__main__":
    unittest.main()
