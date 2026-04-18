"""Tests for capturing second-layer raw response snapshots."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from uuid import uuid4

from scripts.intent_eval.capture_second_layer_response_snapshots import (
    CaptureConfig,
    capture_config_from_environment,
    capture_response_snapshots,
    format_capture_case_listing,
    format_empty_capture_selection,
    format_capture_summary,
    load_existing_capture_ids,
    load_capture_cases,
    main,
    select_capture_cases,
    write_capture_records,
)


class StubOpenAIClientFactory:
    def __init__(self, response_texts: list[str]):
        self.response_texts = list(response_texts)
        self.client_calls = []
        self.create_calls = []

    def __call__(self, **kwargs):
        self.client_calls.append(kwargs)
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=self._create_response),
            )
        )

    def _create_response(self, **kwargs):
        self.create_calls.append(kwargs)
        response_text = self.response_texts.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))]
        )


class FailingOpenAIClientFactory:
    def __init__(self):
        self.client_calls = []
        self.create_calls = []

    def __call__(self, **kwargs):
        self.client_calls.append(kwargs)
        return SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=self._create_response),
            )
        )

    def _create_response(self, **kwargs):
        self.create_calls.append(kwargs)
        raise RuntimeError("provider unavailable")


class StubBaseChatLlm:
    def __init__(self, response_texts: list[str]):
        self.response_texts = list(response_texts)
        self.calls = []

    def chat(self, messages, stream=False, **kwargs):
        self.calls.append(
            {
                "messages": messages,
                "stream": stream,
                "kwargs": kwargs,
            }
        )
        return self.response_texts.pop(0)


class CaptureSecondLayerResponseSnapshotsTests(unittest.TestCase):
    def test_capture_records_include_parse_and_validation_details(self) -> None:
        cases = [
            {
                "id": "capture_case_1",
                "category": "mental_care+medication",
                "description": "clarification case",
                "message": "Should I keep taking that medicine every day?",
            },
            {
                "id": "capture_case_2",
                "category": "snapshot_parse_failure",
                "description": "parse failure case",
                "message": "Can you check whether this reply is valid?",
            },
        ]
        client_factory = StubOpenAIClientFactory(
            [
                """```json
                {
                  "status": "needs_clarification",
                  "ready_for_routing": false,
                  "routing_decision": "ask_clarification",
                  "primary_task": null,
                  "secondary_tasks": [],
                  "risk_flags": [],
                  "clarification_question": "Do you want help with medicine or emotional support first?",
                  "notes": "capture test"
                }
                ```""",
                "I cannot decide yet.",
            ]
        )

        records = capture_response_snapshots(
            cases,
            config=CaptureConfig(
                model="glm-5.1",
                api_key="test-key",
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            ),
            client_factory=client_factory,
        )

        self.assertEqual(2, len(records))
        self.assertEqual("needs_clarification", records[0]["parsed_payload"]["status"])
        self.assertTrue(records[0]["validation"]["valid"])
        self.assertEqual("clarification_candidate", records[0]["guard"]["status"])
        self.assertIsNone(records[1]["parsed_payload"])
        self.assertIn("valid JSON object", records[1]["parse_error"])
        self.assertEqual("glm-5.1", client_factory.create_calls[0]["model"])
        self.assertEqual(
            "https://open.bigmodel.cn/api/paas/v4/",
            client_factory.client_calls[0]["base_url"],
        )
        self.assertEqual("openai_compatible", records[0]["request"]["provider"])

    def test_capture_records_can_reuse_base_qwen_style_chat_wrapper(self) -> None:
        cases = [
            {
                "id": "capture_case_base_qwen",
                "category": "profile_memory",
                "description": "base qwen capture case",
                "message": "Please remember that I prefer ginger tea.",
            }
        ]
        llm = StubBaseChatLlm(
            [
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
                    "reason": "save drink preference",
                    "slots": {"memory_key": "favorite_drink"}
                  },
                  "secondary_tasks": [],
                  "risk_flags": [],
                  "notes": "base-qwen-capture"
                }
                ```"""
            ]
        )

        records = capture_response_snapshots(
            cases,
            config=CaptureConfig(
                provider="base_qwen",
                model="qwen-plus",
                temperature=0.1,
            ),
            base_llm_factory=lambda **kwargs: llm,
        )

        self.assertEqual(1, len(records))
        self.assertEqual("base_qwen", records[0]["request"]["provider"])
        self.assertEqual("profile_memory_update", records[0]["parsed_payload"]["primary_task"]["intent"])
        self.assertEqual("qwen-plus", llm.calls[0]["kwargs"]["model"])
        self.assertEqual(0.1, llm.calls[0]["kwargs"]["temperature"])
        self.assertFalse(llm.calls[0]["stream"])

    def test_capture_records_preserve_request_errors_without_aborting_batch(self) -> None:
        cases = [
            {
                "id": "capture_case_error",
                "category": "profile_memory",
                "description": "request error case",
                "message": "Please remember that I prefer ginger tea.",
            }
        ]

        records = capture_response_snapshots(
            cases,
            config=CaptureConfig(
                provider="openai_compatible",
                model="glm-5.1",
                api_key="test-key",
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            ),
            client_factory=FailingOpenAIClientFactory(),
        )

        self.assertEqual(1, len(records))
        self.assertEqual("", records[0]["raw_response_text"])
        self.assertIn("request_error:", records[0]["parse_error"])
        self.assertIn("RuntimeError", records[0]["request_error"])
        self.assertIsNone(records[0]["validation"])
        self.assertIsNone(records[0]["guard"])

    def test_write_capture_records_outputs_jsonl(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"capture-snapshots-test-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            output_path = temp_dir / "captured.jsonl"
            write_capture_records(
                [
                    {
                        "id": "capture_case_1",
                        "category": "mental_care+medication",
                        "message": "test message",
                        "raw_response_text": "{}",
                        "parsed_payload": {},
                        "parse_error": None,
                        "validation": {"valid": False},
                    }
                ],
                output_path,
            )

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(1, len(lines))
        self.assertIn("\"capture_case_1\"", lines[0])

    def test_format_capture_summary_reports_counts(self) -> None:
        text = format_capture_summary(
            [
                {"category": "a", "validation": {"valid": True}, "parse_error": None},
                {
                    "category": "b",
                    "validation": {"valid": False},
                    "parse_error": "boom",
                    "request_error": "RuntimeError: boom",
                },
            ],
            Path(".runtime") / "capture.jsonl",
        )

        self.assertIn("VitalAI second-layer snapshot capture: OK", text)
        self.assertIn("records: total=2 valid=1 invalid=1", text)
        self.assertIn("parse_failures: 1", text)
        self.assertIn("request_errors: 1", text)

    def test_capture_case_dataset_loads(self) -> None:
        cases = load_capture_cases(
            Path("data") / "intent_eval" / "second_layer_capture_cases.jsonl"
        )

        self.assertGreaterEqual(len(cases), 16)
        self.assertEqual("capture_001_medication_emotion", cases[0]["id"])
        self.assertEqual("capture_016_medication_aftereffect", cases[-1]["id"])

    def test_select_capture_cases_filters_by_category_and_limit(self) -> None:
        cases = [
            {"id": "case_1", "category": "health"},
            {"id": "case_2", "category": "health"},
            {"id": "case_3", "category": "profile_memory"},
        ]

        selected = select_capture_cases(cases, categories=["health"], limit=1)

        self.assertEqual(1, len(selected))
        self.assertEqual("case_1", selected[0]["id"])

    def test_select_capture_cases_rejects_unknown_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown capture-case id"):
            select_capture_cases(
                [{"id": "case_1", "category": "health"}],
                case_ids=["missing_case"],
            )

    def test_select_capture_cases_can_skip_existing_ids(self) -> None:
        selected = select_capture_cases(
            [
                {"id": "case_1", "category": "health"},
                {"id": "case_2", "category": "health"},
            ],
            excluded_ids={"case_1"},
        )

        self.assertEqual(["case_2"], [case["id"] for case in selected])

    def test_list_cases_mode_does_not_require_llm_environment(self) -> None:
        exit_code = main(
            [
                "--list-cases",
                "--category",
                "profile_memory",
                "--limit",
                "1",
            ]
        )

        self.assertEqual(0, exit_code)

    def test_format_capture_case_listing_reports_selected_cases(self) -> None:
        text = format_capture_case_listing(
            [
                {
                    "id": "case_1",
                    "category": "health",
                    "description": "health-focused sample",
                }
            ]
        )

        self.assertIn("VitalAI second-layer capture cases", text)
        self.assertIn("selected_cases: 1", text)
        self.assertIn("case_1 [health]", text)

    def test_load_existing_capture_ids_reads_existing_jsonl(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"capture-existing-test-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            output_path = temp_dir / "captured.jsonl"
            output_path.write_text(
                "\n".join(
                    [
                        '{"id":"case_1","category":"health"}',
                        '{"id":"case_2","category":"profile_memory"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            captured_ids = load_existing_capture_ids(output_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual({"case_1", "case_2"}, captured_ids)

    def test_empty_capture_selection_message_is_stable(self) -> None:
        text = format_empty_capture_selection(
            output_path=Path(".runtime") / "capture.jsonl",
            skipped_existing=3,
        )

        self.assertIn("nothing to do", text)
        self.assertIn("skipped_existing: 3", text)

    def test_list_cases_with_skip_existing_excludes_existing_cases(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"capture-skip-existing-test-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            output_path = temp_dir / "captured.jsonl"
            output_path.write_text(
                '{"id":"capture_009_memory_update_safe","category":"profile_memory"}\n',
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--list-cases",
                    "--category",
                    "profile_memory",
                    "--skip-existing",
                    "--output",
                    str(output_path),
                ]
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(0, exit_code)

    def test_capture_config_from_environment_supports_base_qwen_without_explicit_openai_envs(self) -> None:
        keys = [
            "VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER",
            "VITALAI_INTENT_DECOMPOSER_LLM_MODEL",
            "VITALAI_INTENT_DECOMPOSER_LLM_API_KEY",
            "VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL",
            "VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE",
            "VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS",
        ]
        previous = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER"] = "base_qwen"
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_MODEL", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_API_KEY", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL", None)
            os.environ["VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE"] = "0.2"
            os.environ["VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS"] = "7.5"

            config = capture_config_from_environment()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual("base_qwen", config.provider)
        self.assertIsNone(config.model)
        self.assertIsNone(config.api_key)
        self.assertIsNone(config.base_url)
        self.assertEqual(0.2, config.temperature)
        self.assertEqual(7.5, config.timeout_seconds)

    def test_capture_config_defaults_base_qwen_timeout_when_unset(self) -> None:
        keys = [
            "VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER",
            "VITALAI_INTENT_DECOMPOSER_LLM_MODEL",
            "VITALAI_INTENT_DECOMPOSER_LLM_API_KEY",
            "VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL",
            "VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE",
            "VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS",
        ]
        previous = {key: os.environ.get(key) for key in keys}
        try:
            os.environ["VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER"] = "base_qwen"
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_MODEL", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_API_KEY", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE", None)
            os.environ.pop("VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS", None)

            config = capture_config_from_environment()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual("base_qwen", config.provider)
        self.assertEqual(30.0, config.timeout_seconds)


if __name__ == "__main__":
    unittest.main()
