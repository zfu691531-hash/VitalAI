"""Tests for minimal user-input preprocessing."""

from __future__ import annotations

import unittest

from VitalAI.application import (
    RunUserInputPreprocessingUseCase,
    UserInteractionCommand,
    input_preprocessing_payload,
)


class UserInputPreprocessingTests(unittest.TestCase):
    def test_preprocessor_trims_and_collapses_whitespace(self) -> None:
        result = RunUserInputPreprocessingUseCase().run(
            UserInteractionCommand(
                user_id="elder-input-001",
                channel="manual",
                message="  我   今天\n头晕\t\t不舒服  ",
            )
        )
        payload = input_preprocessing_payload(result)

        self.assertEqual("  我   今天\n头晕\t\t不舒服  ", result.original_message)
        self.assertEqual("我 今天 头晕 不舒服", result.normalized_message)
        self.assertTrue(result.changed)
        self.assertIn("message_normalized", {flag["kind"] for flag in payload["flags"]})

    def test_preprocessor_flags_empty_message_after_normalization(self) -> None:
        result = RunUserInputPreprocessingUseCase().run(
            UserInteractionCommand(
                user_id="elder-input-002",
                channel="manual",
                message="   \n\t  ",
            )
        )

        self.assertEqual("", result.normalized_message)
        self.assertIn("empty_after_normalization", {flag.kind for flag in result.flags})

    def test_preprocessor_flags_non_whitespace_control_characters(self) -> None:
        result = RunUserInputPreprocessingUseCase().run(
            UserInteractionCommand(
                user_id="elder-input-003",
                channel="manual",
                message="hello\x00world",
            )
        )

        self.assertIn("control_character_signal", {flag.kind for flag in result.flags})


if __name__ == "__main__":
    unittest.main()
