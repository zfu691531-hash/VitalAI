"""Tests for the backend-only user interaction workflow."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch

from VitalAI.application import (
    LLMIntentDecomposer,
    IntentDecompositionResult,
    IntentDecompositionTask,
    IntentDecompositionValidationResult,
    OpenAICompatibleIntentDecompositionBackend,
    RunIntentDecompositionUseCase,
    UserInteractionCommand,
    UserInteractionEventType,
    build_application_assembly_from_environment_for_role,
)


class StubRouteCandidateDecomposer:
    def decompose(self, command, intent_result):
        return IntentDecompositionValidationResult(
            valid=True,
            result=IntentDecompositionResult(
                status="decomposed",
                ready_for_routing=True,
                routing_decision="route_primary",
                source="stub_decomposer",
                primary_task=IntentDecompositionTask(
                    task_type="daily_support",
                    intent=UserInteractionEventType.DAILY_LIFE_CHECKIN,
                    priority=60,
                    confidence=0.88,
                    reason="daily support is safe to propose as a candidate",
                    slots={"need": "meal_support"},
                ),
            ),
        )


class StubClarificationDecomposer:
    def decompose(self, command, intent_result):
        return IntentDecompositionValidationResult(
            valid=True,
            result=IntentDecompositionResult(
                status="needs_clarification",
                ready_for_routing=False,
                routing_decision="ask_clarification",
                source="stub_decomposer",
                clarification_question="Do you want help with medicine or emotional support first?",
            ),
        )


class StubOpenAIClientFactory:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.client_calls = []
        self.create_calls = []

    def __call__(self, **kwargs):
        self.client_calls.append(kwargs)
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=self._create_response,
                )
            )
        )

    def _create_response(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.response_text),
                )
            ]
        )


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
                workflow.run(
                    UserInteractionCommand(
                        user_id="elder-1701",
                        channel="manual",
                        message="I like jazz.",
                        event_type="profile_memory_update",
                        trace_id="trace-interaction-profile-write-music",
                        context={
                            "memory_key": "favorite_music",
                            "memory_value": "jazz",
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
                        context={"memory_key": "favorite_drink"},
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
        self.assertEqual("profile-memory-domain-agent", update_result.agent_cycles[0]["agent_id"])
        self.assertEqual("store_profile_memory", update_result.agent_cycles[0]["decision"]["decision_type"])
        self.assertTrue(query_result.accepted)
        self.assertEqual("PROFILE_MEMORY_QUERY", query_result.routed_event_type)
        self.assertEqual("profile_memory_snapshot_loaded", query_result.response)
        self.assertEqual(1, query_result.memory_updates["profile_snapshot"]["memory_count"])
        self.assertEqual(["favorite_drink"], query_result.memory_updates["profile_snapshot"]["memory_keys"])
        self.assertEqual(
            "1 profile memory entry: favorite_drink",
            query_result.memory_updates["profile_snapshot"]["readable_summary"],
        )
        self.assertEqual("favorite_drink", query_result.memory_updates["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual(
            "ginger_tea",
            query_result.memory_updates["profile_snapshot"]["entries"][0]["memory_value"],
        )
        self.assertEqual("profile-memory-domain-agent", update_result.agent_handoffs[1]["agent_id"])
        self.assertEqual("domain_agent", update_result.agent_handoffs[1]["role"])
        self.assertEqual("profile-memory-domain-agent", query_result.agent_handoffs[1]["agent_id"])
        self.assertEqual("load_profile_memory", query_result.agent_cycles[0]["decision"]["decision_type"])

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
        self.assertEqual("immediate_review", result.actions[0]["priority"])
        self.assertEqual("health-domain-agent", result.agent_handoffs[1]["agent_id"])
        self.assertEqual("domain_agent", result.agent_handoffs[1]["role"])
        self.assertEqual("health-domain-agent", result.agent_cycles[0]["agent_id"])
        self.assertEqual("raise_health_alert", result.agent_cycles[0]["decision"]["decision_type"])
        self.assertEqual("critical", result.agent_cycles[0]["decision"]["payload"]["risk_assessment"]["level"])
        self.assertEqual(
            "immediate_review",
            result.agent_cycles[0]["decision"]["payload"]["action_plan"]["followup_priority"],
        )
        self.assertEqual("critical", result.agent_cycles[0]["execution"]["payload"]["stored_risk_level"])
        self.assertEqual("raised", result.agent_cycles[0]["execution"]["payload"]["status"])

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
        self.assertEqual("critical", result.agent_cycles[0]["decision"]["payload"]["risk_assessment"]["level"])
        self.assertIn(
            "fall_signal",
            result.agent_cycles[0]["decision"]["payload"]["risk_assessment"]["signal_tags"],
        )
        self.assertEqual("immediate_review", result.actions[0]["priority"])

    def test_interaction_workflow_preprocesses_message_before_intent_recognition(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1711",
                channel="manual",
                message="  我刚刚   摔倒了，\n现在有点头晕  ",
                trace_id="trace-interaction-preprocessed-health",
            )
        )

        self.assertTrue(result.accepted)
        self.assertEqual("HEALTH_ALERT", result.routed_event_type)
        self.assertEqual("我刚刚 摔倒了， 现在有点头晕", result.preprocessing["normalized_message"])
        self.assertEqual(
            "  我刚刚   摔倒了，\n现在有点头晕  ",
            result.preprocessing["original_message"],
        )
        self.assertTrue(result.preprocessing["changed"])

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
        self.assertEqual("intent-recognition-agent", result.agent_handoffs[1]["agent_id"])

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
        self.assertEqual("intent-decomposition-agent", result.agent_handoffs[2]["agent_id"])
        self.assertEqual(
            "pending_second_layer",
            result.error_details["decomposition"]["status"],
        )
        self.assertFalse(result.error_details["decomposition"]["ready_for_routing"])
        self.assertEqual(
            "hold_for_second_layer_decomposition",
            result.error_details["decomposition"]["routing_decision"],
        )
        self.assertEqual(
            "hold_for_second_layer",
            result.error_details["decomposition_guard"]["status"],
        )
        self.assertFalse(result.error_details["decomposition_guard"]["candidate_ready"])

    def test_interaction_workflow_holds_guarded_route_candidate_without_execution(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()
        workflow.intent_decomposition_use_case = RunIntentDecompositionUseCase(
            decomposer=StubRouteCandidateDecomposer()
        )

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1709",
                channel="manual",
                message=(
                    "\u6211\u8fd9\u4e24\u5929\u5934\u6709\u70b9\u6655\uff0c"
                    "\u4e0d\u77e5\u9053\u662f\u4e0d\u662f\u6628\u5929\u4e70\u83dc\u8d70\u592a\u591a\u8def\u4e86\u3002"
                ),
            )
        )

        guard = result.error_details["decomposition_guard"]

        self.assertFalse(result.accepted)
        self.assertEqual("decomposition_needed", result.error)
        self.assertIsNone(result.routed_event_type)
        self.assertEqual([], result.actions)
        self.assertEqual("routing_candidate", guard["status"])
        self.assertTrue(guard["candidate_ready"])
        self.assertEqual("daily_life_checkin", guard["routing_candidate"]["intent"])

    def test_interaction_workflow_returns_decomposition_clarification_candidate(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        workflow = assembly.build_user_interaction_workflow()
        workflow.intent_decomposition_use_case = RunIntentDecompositionUseCase(
            decomposer=StubClarificationDecomposer()
        )

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1710",
                channel="manual",
                message=(
                    "\u6211\u5fc3\u91cc\u8001\u662f\u614c\u614c\u7684\uff0c"
                    "\u90a3\u4e2a\u836f\u6211\u5230\u5e95\u8981\u4e0d\u8981\u5929\u5929\u5403\u554a\u3002"
                ),
            )
        )

        guard = result.error_details["decomposition_guard"]

        self.assertFalse(result.accepted)
        self.assertEqual("decomposition_needed", result.error)
        self.assertEqual("clarification_candidate", guard["status"])
        self.assertFalse(guard["candidate_ready"])
        self.assertEqual(
            "Do you want help with medicine or emotional support first?",
            result.response,
        )

    def test_interaction_workflow_can_use_env_wired_openai_compatible_decomposer(self) -> None:
        client_factory = StubOpenAIClientFactory(
            """{
              "status": "needs_clarification",
              "ready_for_routing": false,
              "routing_decision": "ask_clarification",
              "primary_task": null,
              "secondary_tasks": [],
              "risk_flags": [
                {
                  "kind": "medication_signal",
                  "severity": "medium",
                  "reason": "medicine question present"
                }
              ],
              "clarification_question": "你是想先确认吃药的问题，还是先聊一下现在心慌的感受？",
              "notes": "stub env-wired llm response"
            }"""
        )
        with patch.dict(
            "os.environ",
            {
                "VITALAI_INTENT_DECOMPOSER": "llm",
                "VITALAI_INTENT_DECOMPOSER_LLM_MODEL": "glm-5.1",
                "VITALAI_INTENT_DECOMPOSER_LLM_API_KEY": "test-key",
                "VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
                "VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE": "0.0",
                "VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS": "5.0",
            },
            clear=False,
        ):
            assembly = build_application_assembly_from_environment_for_role("api")
            workflow = assembly.build_user_interaction_workflow()

        decomposer = workflow.intent_decomposition_use_case.decomposer
        self.assertIsInstance(decomposer, LLMIntentDecomposer)
        self.assertIsInstance(decomposer.backend, OpenAICompatibleIntentDecompositionBackend)
        decomposer.backend.client_factory = client_factory

        result = workflow.run(
            UserInteractionCommand(
                user_id="elder-1712",
                channel="manual",
                message=(
                    "我心里老是慌慌的，"
                    "那个药我到底要不要天天吃啊。"
                ),
                trace_id="trace-interaction-env-llm-decomposer",
            )
        )

        guard = result.error_details["decomposition_guard"]

        self.assertFalse(result.accepted)
        self.assertEqual("decomposition_needed", result.error)
        self.assertEqual(
            "你是想先确认吃药的问题，还是先聊一下现在心慌的感受？",
            result.response,
        )
        self.assertEqual("needs_clarification", result.error_details["decomposition"]["status"])
        self.assertEqual("llm_schema_validated", result.error_details["decomposition"]["source"])
        self.assertEqual("clarification_candidate", guard["status"])
        self.assertFalse(guard["candidate_ready"])
        self.assertEqual("glm-5.1", client_factory.create_calls[0]["model"])
        self.assertEqual(
            "https://open.bigmodel.cn/api/paas/v4/",
            client_factory.client_calls[0]["base_url"],
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
        self.assertEqual("", result.preprocessing["normalized_message"])
        self.assertIn(
            "empty_after_normalization",
            {flag["kind"] for flag in result.preprocessing["flags"]},
        )

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
