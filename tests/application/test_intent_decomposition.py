"""Tests for the second-layer intent decomposition placeholder."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from VitalAI.application import (
    BaseLlmIntentDecompositionBackend,
    LLMIntentDecomposer,
    OpenAICompatibleIntentDecompositionBackend,
    parse_intent_decomposition_response_text,
    RuleBasedIntentRecognizer,
    IntentDecompositionRiskFlag,
    IntentDecompositionResult,
    IntentDecompositionTask,
    RunIntentDecompositionUseCase,
    RunIntentDecompositionRoutingGuardUseCase,
    RunIntentDecompositionValidationUseCase,
    UserInteractionCommand,
    UserInteractionEventType,
    intent_decomposition_llm_output_schema,
    intent_decomposition_payload,
    intent_decomposition_routing_guard_payload,
    intent_decomposition_validation_payload,
)


class StubValidDecompositionBackend:
    def generate(self, command, intent_result, schema):
        return {
            "status": "decomposed",
            "ready_for_routing": True,
            "routing_decision": "route_primary",
            "primary_task": {
                "task_type": "health_review",
                "intent": "health_alert",
                "priority": 10,
                "confidence": 0.92,
                "reason": "validated stub health task",
                "slots": {"symptom": "头晕"},
            },
            "secondary_tasks": [],
            "risk_flags": [
                {
                    "kind": "health_signal",
                    "severity": "high",
                    "reason": "stub health risk",
                }
            ],
            "notes": "stub valid payload",
        }


class StubInvalidDecompositionBackend:
    def generate(self, command, intent_result, schema):
        return {
            "status": "decomposed",
            "ready_for_routing": True,
            "routing_decision": "route_primary",
            "primary_task": None,
        }


class FailingDecompositionBackend:
    def generate(self, command, intent_result, schema):
        raise RuntimeError("boom")


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
                    create=self._create_response
                )
            )
        )

    def _create_response(self, **create_kwargs):
        self.create_calls.append(create_kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.response_text),
                )
            ]
        )


class StubBaseChatLlm:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    def chat(self, messages, stream=False, **kwargs):
        self.calls.append(
            {
                "messages": messages,
                "stream": stream,
                "kwargs": kwargs,
            }
        )
        return self.response_text


class IntentDecompositionTests(unittest.TestCase):
    def test_placeholder_preserves_first_layer_candidates_without_routing(self) -> None:
        command = UserInteractionCommand(
            user_id="elder-2101",
            channel="manual",
            message=(
                "\u6211\u5fc3\u91cc\u8001\u662f\u614c\u614c\u7684\uff0c"
                "\u90a3\u4e2a\u836f\u6211\u5230\u5e95\u8981\u4e0d\u8981\u5929\u5929\u5403\u554a\u3002"
            ),
        )
        intent_result = RuleBasedIntentRecognizer().recognize(command)

        result = RunIntentDecompositionUseCase().run(command, intent_result)
        payload = intent_decomposition_payload(result)

        self.assertEqual("pending_second_layer", result.status)
        self.assertFalse(result.ready_for_routing)
        self.assertEqual("hold_for_second_layer_decomposition", result.routing_decision)
        self.assertIsNone(result.primary_task)
        self.assertGreaterEqual(len(result.candidate_tasks), 2)
        self.assertIn("mental_care_checkin", {task["intent"] for task in payload["candidate_tasks"]})
        self.assertIn("health_alert", {task["intent"] for task in payload["candidate_tasks"]})
        self.assertIn("medication_signal", {flag["kind"] for flag in payload["risk_flags"]})

    def test_llm_schema_accepts_valid_routable_payload(self) -> None:
        raw_payload = {
            "status": "decomposed",
            "ready_for_routing": True,
            "routing_decision": "route_sequence",
            "primary_task": {
                "task_type": "health_review",
                "intent": "health_alert",
                "priority": 10,
                "confidence": 0.91,
                "reason": "health risk should be reviewed first",
                "slots": {"symptom": "胸口闷"},
            },
            "secondary_tasks": [
                {
                    "task_type": "daily_context",
                    "intent": "daily_life_checkin",
                    "priority": 60,
                    "confidence": 0.65,
                    "reason": "housework context is secondary",
                    "slots": {"context": "收拾屋子"},
                }
            ],
            "risk_flags": [
                {
                    "kind": "health_signal",
                    "severity": "high",
                    "reason": "chest discomfort mentioned",
                }
            ],
            "notes": "validated fixture",
        }

        validation = RunIntentDecompositionValidationUseCase().run(raw_payload)
        payload = intent_decomposition_validation_payload(validation)

        self.assertTrue(validation.valid)
        self.assertIsNotNone(validation.result)
        self.assertEqual("route_sequence", validation.result.routing_decision)
        self.assertEqual("health_alert", payload["result"]["primary_task"]["intent"])
        self.assertEqual("daily_life_checkin", payload["result"]["secondary_tasks"][0]["intent"])
        self.assertEqual("high", payload["result"]["risk_flags"][0]["severity"])

    def test_llm_schema_rejects_invalid_or_unsafe_routing_payload(self) -> None:
        raw_payload = {
            "status": "decomposed",
            "ready_for_routing": True,
            "routing_decision": "route_primary",
            "primary_task": None,
            "secondary_tasks": [
                {
                    "task_type": "bad_task",
                    "intent": "unsupported_intent",
                    "priority": 120,
                    "confidence": 1.2,
                    "slots": [],
                }
            ],
            "risk_flags": [
                {
                    "kind": "unknown",
                    "severity": "urgent",
                    "reason": "bad enum",
                }
            ],
        }

        validation = RunIntentDecompositionValidationUseCase().run(raw_payload)
        issues = intent_decomposition_validation_payload(validation)["issues"]
        issue_codes = {issue["code"] for issue in issues}

        self.assertFalse(validation.valid)
        self.assertIsNone(validation.result)
        self.assertIn("required_for_routing", issue_codes)
        self.assertIn("unsupported_intent", issue_codes)
        self.assertIn("out_of_range", issue_codes)
        self.assertIn("unsupported_value", issue_codes)

    def test_llm_output_schema_is_exposed_for_adapter_contracts(self) -> None:
        schema = intent_decomposition_llm_output_schema()

        self.assertEqual("object", schema["type"])
        self.assertIn("status", schema["required"])
        self.assertIn("routing_decision", schema["properties"])
        self.assertIn("routing_guards", schema)

    def test_llm_decomposer_validates_backend_payload(self) -> None:
        command, intent_result = _compound_command_and_intent()

        validation = LLMIntentDecomposer(
            backend=StubValidDecompositionBackend(),
        ).decompose(command, intent_result)

        self.assertTrue(validation.valid)
        self.assertIsNotNone(validation.result)
        self.assertEqual("llm_schema_validated", validation.result.source)
        self.assertEqual("route_primary", validation.result.routing_decision)
        self.assertEqual("health_alert", validation.result.primary_task.intent.value)

    def test_llm_decomposer_returns_validation_issues_for_invalid_payload(self) -> None:
        command, intent_result = _compound_command_and_intent()

        validation = LLMIntentDecomposer(
            backend=StubInvalidDecompositionBackend(),
        ).decompose(command, intent_result)

        self.assertFalse(validation.valid)
        self.assertIsNone(validation.result)
        self.assertIn("required_for_routing", {issue.code for issue in validation.issues})

    def test_llm_decomposer_falls_back_to_placeholder_on_backend_error(self) -> None:
        command, intent_result = _compound_command_and_intent()

        validation = LLMIntentDecomposer(
            backend=FailingDecompositionBackend(),
        ).decompose(command, intent_result)

        self.assertTrue(validation.valid)
        self.assertIsNotNone(validation.result)
        self.assertEqual("pending_second_layer", validation.result.status)
        self.assertEqual("placeholder_intent_decomposer", validation.result.source)

    def test_openai_compatible_backend_can_parse_json_code_fence_response(self) -> None:
        backend_factory = StubOpenAIClientFactory(
            """```json
            {
              "status": "decomposed",
              "ready_for_routing": true,
              "routing_decision": "route_primary",
              "primary_task": {
                "task_type": "mental_support",
                "intent": "mental_care_checkin",
                "priority": 30,
                "confidence": 0.82,
                "reason": "emotional support is primary",
                "slots": {
                  "support_need": "companionship"
                }
              },
              "secondary_tasks": [],
              "candidate_tasks": [],
              "risk_flags": [],
              "notes": "stub openai-compatible response"
            }
            ```"""
        )
        command, intent_result = _compound_command_and_intent()

        payload = OpenAICompatibleIntentDecompositionBackend(
            model="glm-5.1",
            api_key="test-key",
            base_url="https://example.invalid/v1",
            client_factory=backend_factory,
        ).generate(
            command,
            intent_result,
            intent_decomposition_llm_output_schema(),
        )

        self.assertEqual("decomposed", payload["status"])
        self.assertEqual("mental_care_checkin", payload["primary_task"]["intent"])
        self.assertEqual("glm-5.1", backend_factory.create_calls[0]["model"])
        self.assertEqual("https://example.invalid/v1", backend_factory.client_calls[0]["base_url"])

    def test_parse_response_text_can_extract_json_from_prose_wrapper(self) -> None:
        payload = parse_intent_decomposition_response_text(
            """Here is the JSON result:

            {
              "status": "decomposed",
              "ready_for_routing": true,
              "routing_decision": "route_primary",
              "primary_task": {
                "task_type": "memory_update",
                "intent": "profile_memory_update",
                "priority": 40,
                "confidence": 0.88,
                "reason": "save a user preference",
                "slots": {
                  "memory_key": "preference",
                  "memory_value": "ginger tea"
                }
              },
              "secondary_tasks": [],
              "risk_flags": [],
              "notes": "prose-wrapped response"
            }

            Thanks."""
        )

        self.assertEqual("decomposed", payload["status"])
        self.assertEqual("profile_memory_update", payload["primary_task"]["intent"])

    def test_base_llm_backend_can_reuse_existing_chat_wrapper(self) -> None:
        command, intent_result = _compound_command_and_intent()
        llm = StubBaseChatLlm(
            """```json
            {
              "status": "decomposed",
              "ready_for_routing": true,
              "routing_decision": "route_primary",
              "primary_task": {
                "task_type": "memory_update",
                "intent": "profile_memory_update",
                "priority": 40,
                "confidence": 0.88,
                "reason": "save a user preference",
                "slots": {
                  "memory_key": "favorite_drink"
                }
              },
              "secondary_tasks": [],
              "risk_flags": [],
              "notes": "base-qwen"
            }
            ```"""
        )

        payload = BaseLlmIntentDecompositionBackend(
            llm=llm,
            model="qwen-plus",
            temperature=0.1,
        ).generate(
            command,
            intent_result,
            intent_decomposition_llm_output_schema(),
        )

        self.assertEqual("profile_memory_update", payload["primary_task"]["intent"])
        self.assertEqual("base-qwen", payload["notes"])
        self.assertEqual("qwen-plus", llm.calls[0]["kwargs"]["model"])
        self.assertEqual(0.1, llm.calls[0]["kwargs"]["temperature"])
        self.assertFalse(llm.calls[0]["stream"])

    def test_routing_guard_exposes_non_executable_route_candidate(self) -> None:
        decomposition = IntentDecompositionResult(
            status="decomposed",
            ready_for_routing=True,
            routing_decision="route_primary",
            source="llm_schema_validated",
            primary_task=IntentDecompositionTask(
                task_type="daily_support",
                intent=UserInteractionEventType.DAILY_LIFE_CHECKIN,
                priority=60,
                confidence=0.86,
                reason="daily-life need is primary",
                slots={"need": "meal_support"},
            ),
        )

        guard = RunIntentDecompositionRoutingGuardUseCase().run(decomposition)
        payload = intent_decomposition_routing_guard_payload(guard)

        self.assertEqual("routing_candidate", guard.status)
        self.assertTrue(guard.candidate_ready)
        self.assertEqual("daily_life_checkin", payload["routing_candidate"]["intent"])
        self.assertEqual("route_primary", payload["routing_candidate"]["routing_decision"])

    def test_routing_guard_turns_clarification_decision_into_candidate(self) -> None:
        decomposition = IntentDecompositionResult(
            status="needs_clarification",
            ready_for_routing=False,
            routing_decision="ask_clarification",
            source="llm_schema_validated",
            clarification_question="Do you want help with medicine or emotional support first?",
        )

        guard = RunIntentDecompositionRoutingGuardUseCase().run(decomposition)

        self.assertEqual("clarification_candidate", guard.status)
        self.assertFalse(guard.candidate_ready)
        self.assertEqual(
            "Do you want help with medicine or emotional support first?",
            guard.clarification_question,
        )

    def test_routing_guard_blocks_high_risk_route_candidate(self) -> None:
        decomposition = IntentDecompositionResult(
            status="decomposed",
            ready_for_routing=True,
            routing_decision="route_primary",
            source="llm_schema_validated",
            primary_task=IntentDecompositionTask(
                task_type="health_review",
                intent=UserInteractionEventType.HEALTH_ALERT,
                priority=10,
                confidence=0.91,
                reason="health signal is primary",
            ),
            risk_flags=(
                IntentDecompositionRiskFlag(
                    kind="health_signal",
                    severity="high",
                    reason="chest discomfort mentioned",
                ),
            ),
        )

        guard = RunIntentDecompositionRoutingGuardUseCase().run(decomposition)

        self.assertEqual("hold_for_human_review", guard.status)
        self.assertFalse(guard.candidate_ready)
        self.assertIn("high_risk:health_signal", guard.blocked_reasons)

def _compound_command_and_intent():
    command = UserInteractionCommand(
        user_id="elder-2102",
        channel="manual",
        message=(
            "\u6211\u5fc3\u91cc\u8001\u662f\u614c\u614c\u7684\uff0c"
            "\u90a3\u4e2a\u836f\u6211\u5230\u5e95\u8981\u4e0d\u8981\u5929\u5929\u5403\u554a\u3002"
        ),
    )
    return command, RuleBasedIntentRecognizer().recognize(command)


if __name__ == "__main__":
    unittest.main()
