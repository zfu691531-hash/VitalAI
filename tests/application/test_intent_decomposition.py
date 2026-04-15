"""Tests for the second-layer intent decomposition placeholder."""

from __future__ import annotations

import unittest

from VitalAI.application import (
    LLMIntentDecomposer,
    RuleBasedIntentRecognizer,
    RunIntentDecompositionUseCase,
    RunIntentDecompositionValidationUseCase,
    UserInteractionCommand,
    intent_decomposition_llm_output_schema,
    intent_decomposition_payload,
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
