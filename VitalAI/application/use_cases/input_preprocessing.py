"""Minimal user-input preprocessing for backend-only interactions."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from VitalAI.application.commands import UserInteractionCommand


@dataclass(frozen=True, slots=True)
class UserInputPreprocessingFlag:
    """One lightweight preprocessing signal for audit and diagnostics."""

    kind: str
    severity: str
    reason: str


@dataclass(frozen=True, slots=True)
class UserInputPreprocessingResult:
    """Normalized input text and audit metadata for one interaction."""

    original_message: str
    normalized_message: str
    changed: bool
    flags: tuple[UserInputPreprocessingFlag, ...] = ()


@dataclass(slots=True)
class RunUserInputPreprocessingUseCase:
    """Normalize user text without adding product-level chat behavior."""

    long_message_threshold: int = 2000

    def run(self, command: UserInteractionCommand) -> UserInputPreprocessingResult:
        """Return normalized message text and non-blocking audit flags."""
        original_message = command.message
        normalized_message = _normalize_message(original_message)
        flags = _preprocessing_flags(
            original_message=original_message,
            normalized_message=normalized_message,
            long_message_threshold=self.long_message_threshold,
        )
        return UserInputPreprocessingResult(
            original_message=original_message,
            normalized_message=normalized_message,
            changed=original_message != normalized_message,
            flags=tuple(flags),
        )


def input_preprocessing_payload(
    result: UserInputPreprocessingResult,
) -> dict[str, object]:
    """Serialize input preprocessing metadata for API diagnostics."""
    return {
        "original_message": result.original_message,
        "normalized_message": result.normalized_message,
        "changed": result.changed,
        "flags": [
            {"kind": flag.kind, "severity": flag.severity, "reason": flag.reason}
            for flag in result.flags
        ],
    }


def _normalize_message(message: str) -> str:
    """Trim and collapse whitespace while preserving language content."""
    return re.sub(r"\s+", " ", message.strip())


def _preprocessing_flags(
    *,
    original_message: str,
    normalized_message: str,
    long_message_threshold: int,
) -> list[UserInputPreprocessingFlag]:
    """Return non-blocking flags observed during minimal preprocessing."""
    flags: list[UserInputPreprocessingFlag] = []
    if normalized_message == "":
        flags.append(
            UserInputPreprocessingFlag(
                kind="empty_after_normalization",
                severity="medium",
                reason="message is empty after trimming whitespace",
            )
        )
    if original_message != normalized_message:
        flags.append(
            UserInputPreprocessingFlag(
                kind="message_normalized",
                severity="info",
                reason="leading/trailing or repeated whitespace was normalized",
            )
        )
    if len(normalized_message) > long_message_threshold:
        flags.append(
            UserInputPreprocessingFlag(
                kind="long_message",
                severity="low",
                reason="message exceeds the configured long-message threshold",
            )
        )
    if _contains_non_whitespace_control_character(original_message):
        flags.append(
            UserInputPreprocessingFlag(
                kind="control_character_signal",
                severity="medium",
                reason="message contains non-whitespace control characters",
            )
        )
    return flags


def _contains_non_whitespace_control_character(text: str) -> bool:
    """Return whether text contains control characters other than whitespace."""
    for character in text:
        if character.isspace():
            continue
        if unicodedata.category(character).startswith("C"):
            return True
    return False
