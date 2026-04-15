"""Tests for minimal backend-only intent recognition."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import unittest

from VitalAI.application import (
    BertIntentRecognizer,
    BertIntentPrediction,
    HybridIntentRecognizer,
    IntentDatasetExample,
    IntentRecognizerMode,
    RuleBasedIntentRecognizer,
    RunIntentRecognitionEvaluationUseCase,
    UserInteractionCommand,
    UserInteractionEventType,
    build_intent_recognition_use_case,
    build_intent_recognizer,
    filter_intent_dataset_examples_by_splits,
    load_intent_dataset_examples_from_jsonl,
    parse_bert_intent_label_map,
)


class StubBertBackend:
    def __init__(self, label: str, confidence: float) -> None:
        self.label = label
        self.confidence = confidence

    def predict(self, text: str) -> BertIntentPrediction:
        return BertIntentPrediction(label=self.label, confidence=self.confidence)


class FailingBertBackend:
    def predict(self, text: str) -> BertIntentPrediction:
        raise RuntimeError("boom")


class IntentRecognitionTests(unittest.TestCase):
    def test_rule_based_recognizer_detects_health_alert(self) -> None:
        result = RuleBasedIntentRecognizer().recognize(
            UserInteractionCommand(
                user_id="elder-1901",
                channel="manual",
                message="我今天头晕，而且有点不舒服",
            )
        )

        self.assertEqual(UserInteractionEventType.HEALTH_ALERT, result.primary_intent)
        self.assertGreaterEqual(result.confidence, 0.7)
        self.assertEqual("high", result.context_updates["risk_level"])

    def test_rule_based_recognizer_detects_profile_memory_update(self) -> None:
        result = RuleBasedIntentRecognizer().recognize(
            UserInteractionCommand(
                user_id="elder-1902",
                channel="manual",
                message="帮我记住我喜欢喝姜茶",
            )
        )

        self.assertEqual(UserInteractionEventType.PROFILE_MEMORY_UPDATE, result.primary_intent)
        self.assertEqual("general_note", result.context_updates["memory_key"])
        self.assertEqual("帮我记住我喜欢喝姜茶", result.context_updates["memory_value"])

    def test_rule_based_recognizer_requests_clarification_for_unknown_text(self) -> None:
        result = RuleBasedIntentRecognizer().recognize(
            UserInteractionCommand(
                user_id="elder-1903",
                channel="manual",
                message="你好",
            )
        )

        self.assertIsNone(result.primary_intent)
        self.assertTrue(result.requires_clarification)
        self.assertIsNotNone(result.clarification_prompt)

    def test_rule_based_recognizer_marks_compound_language_for_decomposition(self) -> None:
        result = RuleBasedIntentRecognizer().recognize(
            UserInteractionCommand(
                user_id="elder-1912",
                channel="manual",
                message=(
                    "\u6211\u5fc3\u91cc\u8001\u662f\u614c\u614c\u7684\uff0c"
                    "\u90a3\u4e2a\u836f\u6211\u5230\u5e95\u8981\u4e0d\u8981\u5929\u5929\u5403\u554a\u3002"
                ),
            )
        )

        self.assertIsNone(result.primary_intent)
        self.assertTrue(result.requires_decomposition)
        self.assertFalse(result.requires_clarification)
        self.assertEqual("needs_decomposition_detector", result.source)
        self.assertGreaterEqual(len(result.candidates), 2)

    def test_intent_dataset_example_round_trips_records(self) -> None:
        example = IntentDatasetExample.from_record(
            {
                "text": "我今天有点头晕",
                "intent": "health_alert",
                "language": "zh",
                "urgency": "high",
                "slots": {"symptom": "头晕"},
                "source": "seed",
                "notes": "health symptom",
            }
        )

        self.assertEqual(UserInteractionEventType.HEALTH_ALERT, example.intent)
        self.assertEqual("头晕", example.slots["symptom"])
        self.assertEqual("seed", example.source)
        self.assertEqual("train", example.split)
        self.assertEqual("health_alert", example.to_record()["intent"])

    def test_intent_dataset_example_accepts_unknown_records(self) -> None:
        example = IntentDatasetExample.from_record(
            {
                "text": "你好",
                "intent": "unknown",
                "language": "zh",
                "slots": {},
            }
        )

        self.assertIsNone(example.intent)
        self.assertEqual("unknown", example.expected_intent_label)
        self.assertEqual("unknown", example.to_record()["intent"])

    def test_seed_intent_dataset_examples_follow_schema(self) -> None:
        dataset_path = Path("docs/intent_dataset_examples.jsonl")

        examples = load_intent_dataset_examples_from_jsonl(dataset_path)

        self.assertEqual(270, len(examples))
        self.assertEqual(
            {
                UserInteractionEventType.HEALTH_ALERT,
                UserInteractionEventType.DAILY_LIFE_CHECKIN,
                UserInteractionEventType.MENTAL_CARE_CHECKIN,
                UserInteractionEventType.PROFILE_MEMORY_UPDATE,
                UserInteractionEventType.PROFILE_MEMORY_QUERY,
                None,
            },
            {example.intent for example in examples},
        )
        self.assertEqual({"train", "dev", "test", "holdout"}, {example.split for example in examples})
        self.assertEqual(
            Counter(
                {
                    "health_alert": 39,
                    "daily_life_checkin": 40,
                    "mental_care_checkin": 38,
                    "profile_memory_update": 40,
                    "profile_memory_query": 40,
                    "unknown": 40,
                    "needs_decomposition": 33,
                }
            ),
            Counter(example.expected_intent_label for example in examples),
        )
        self.assertEqual(90, sum(1 for example in examples if example.split == "holdout"))
        self.assertEqual(33, sum(1 for example in examples if example.requires_decomposition))

    def test_intent_dataset_examples_can_filter_baseline_and_holdout(self) -> None:
        examples = load_intent_dataset_examples_from_jsonl("docs/intent_dataset_examples.jsonl")

        baseline = filter_intent_dataset_examples_by_splits(examples, {"train", "dev", "test"})
        holdout = filter_intent_dataset_examples_by_splits(examples, {"holdout"})

        self.assertEqual(180, len(baseline))
        self.assertEqual(90, len(holdout))
        self.assertEqual({"train", "dev", "test"}, {example.split for example in baseline})
        self.assertEqual({"holdout"}, {example.split for example in holdout})

    def test_offline_intent_evaluation_reports_metrics(self) -> None:
        examples = load_intent_dataset_examples_from_jsonl("docs/intent_dataset_examples.jsonl")

        summary = RunIntentRecognitionEvaluationUseCase(
            recognizer=RuleBasedIntentRecognizer()
        ).run(examples)

        self.assertEqual(len(examples), summary.total)
        self.assertEqual(270, summary.total)
        self.assertEqual(1.0, summary.accuracy)
        self.assertEqual(0, summary.failed)
        self.assertIn("health_alert", summary.by_intent)
        self.assertIn("unknown", summary.by_intent)
        self.assertIn("needs_decomposition", summary.by_intent)
        self.assertIn("rule_based", summary.by_source)
        self.assertEqual(33, summary.by_source["needs_decomposition_detector"]["total"])
        self.assertEqual(0, summary.fallback["total"])
        self.assertEqual(40, summary.clarification["total"])
        self.assertEqual(summary.failed, len(summary.failures))
        self.assertEqual(summary.total, summary.to_report()["total"])
        self.assertIn("by_source", summary.to_report())

    def test_bert_recognizer_shell_falls_back_without_model_path(self) -> None:
        result = BertIntentRecognizer().recognize(
            UserInteractionCommand(
                user_id="elder-1904",
                channel="manual",
                message="我刚刚摔倒了",
            )
        )

        self.assertEqual(UserInteractionEventType.HEALTH_ALERT, result.primary_intent)
        self.assertEqual("bert_model_missing_fallback", result.source)

    def test_bert_recognizer_uses_backend_prediction_above_threshold(self) -> None:
        result = BertIntentRecognizer(
            backend=StubBertBackend("mental_care_checkin", 0.91),
            confidence_threshold=0.65,
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1906",
                channel="manual",
                message="我今天心情不好",
            )
        )

        self.assertEqual(UserInteractionEventType.MENTAL_CARE_CHECKIN, result.primary_intent)
        self.assertEqual("bert", result.source)
        self.assertEqual(0.91, result.confidence)
        self.assertEqual("companionship", result.context_updates["support_need"])

    def test_bert_recognizer_falls_back_below_threshold(self) -> None:
        result = BertIntentRecognizer(
            backend=StubBertBackend("daily_life_checkin", 0.41),
            confidence_threshold=0.65,
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1907",
                channel="manual",
                message="我今天头晕",
            )
        )

        self.assertEqual(UserInteractionEventType.HEALTH_ALERT, result.primary_intent)
        self.assertEqual("bert_low_confidence_fallback", result.source)

    def test_bert_recognizer_requests_clarification_for_unknown_backend_label(self) -> None:
        result = BertIntentRecognizer(
            backend=StubBertBackend("unknown", 0.91),
            confidence_threshold=0.65,
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1908",
                channel="manual",
                message="你好",
            )
        )

        self.assertIsNone(result.primary_intent)
        self.assertEqual("bert", result.source)
        self.assertTrue(result.requires_clarification)

    def test_bert_recognizer_maps_generic_model_labels(self) -> None:
        result = BertIntentRecognizer(
            backend=StubBertBackend("LABEL_2", 0.91),
            confidence_threshold=0.65,
            label_map=(
                "health_alert,daily_life_checkin,mental_care_checkin,"
                "profile_memory_update,profile_memory_query,unknown"
            ),
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1910",
                channel="manual",
                message="我今天心情不太好",
            )
        )

        self.assertEqual(UserInteractionEventType.MENTAL_CARE_CHECKIN, result.primary_intent)
        self.assertEqual("bert", result.source)

    def test_bert_recognizer_handles_unmapped_generic_label_as_clarification(self) -> None:
        result = BertIntentRecognizer(
            backend=StubBertBackend("LABEL_99", 0.91),
            confidence_threshold=0.65,
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1911",
                channel="manual",
                message="你好",
            )
        )

        self.assertIsNone(result.primary_intent)
        self.assertEqual("bert", result.source)
        self.assertTrue(result.requires_clarification)

    def test_parse_bert_intent_label_map_supports_ordered_and_explicit_forms(self) -> None:
        ordered = parse_bert_intent_label_map("health_alert,daily_life_checkin")
        explicit = parse_bert_intent_label_map("LABEL_0=health_alert,1=daily_life_checkin")

        self.assertEqual("health_alert", ordered["0"])
        self.assertEqual("health_alert", ordered["label_0"])
        self.assertEqual("health_alert", explicit["label_0"])
        self.assertEqual("daily_life_checkin", explicit["1"])

    def test_bert_recognizer_falls_back_on_backend_error(self) -> None:
        result = BertIntentRecognizer(
            backend=FailingBertBackend(),
        ).recognize(
            UserInteractionCommand(
                user_id="elder-1909",
                channel="manual",
                message="我刚刚摔倒了",
            )
        )

        self.assertEqual(UserInteractionEventType.HEALTH_ALERT, result.primary_intent)
        self.assertEqual("bert_inference_error_fallback", result.source)

    def test_bert_recognizer_shell_can_report_unavailable_without_fallback(self) -> None:
        result = BertIntentRecognizer(fallback=None).recognize(
            UserInteractionCommand(
                user_id="elder-1905",
                channel="manual",
                message="我刚刚摔倒了",
            )
        )

        self.assertIsNone(result.primary_intent)
        self.assertEqual("bert_unavailable", result.source)
        self.assertTrue(result.requires_clarification)

    def test_build_intent_recognizer_selects_modes(self) -> None:
        self.assertIsInstance(build_intent_recognizer("rule_based"), RuleBasedIntentRecognizer)
        self.assertIsInstance(build_intent_recognizer("bert"), BertIntentRecognizer)
        self.assertIsInstance(build_intent_recognizer(IntentRecognizerMode.HYBRID), HybridIntentRecognizer)
        self.assertIsInstance(build_intent_recognizer("unknown-mode"), RuleBasedIntentRecognizer)
        mapped = build_intent_recognition_use_case(
            mode="bert",
            bert_label_map="0=health_alert",
        ).recognizer
        self.assertIsInstance(mapped, BertIntentRecognizer)
        self.assertEqual("health_alert", mapped.label_map["0"])


if __name__ == "__main__":
    unittest.main()
