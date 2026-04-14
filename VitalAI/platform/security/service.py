"""Lightweight sensitive-data guard for typed platform security reviews."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from VitalAI.platform.interrupt import InterruptSignal
from VitalAI.platform.runtime.event_aggregator import EventSummary
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot
from VitalAI.platform.security.review import (
    SecurityAction,
    SecurityFinding,
    SecurityReviewResult,
    SecuritySeverity,
)

EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_PATTERN = re.compile(r"(?<!\d)(1\d{10}|(?:\+?\d[\d -]{8,}\d))(?!\d)")


@dataclass
class SensitiveDataGuard:
    """Apply lightweight security review and redaction to text and mappings."""

    sensitive_key_markers: tuple[str, ...] = (
        "password",
        "secret",
        "token",
        "api_key",
        "phone",
        "mobile",
        "email",
        "id_card",
    )
    redaction_placeholder: str = "[REDACTED]"
    blocked_text_markers: tuple[str, ...] = ("sk-", "Bearer ")

    def sanitize_text(self, text: str) -> tuple[str, SecurityReviewResult]:
        """Redact lightweight sensitive content from free text."""
        sanitized = text
        findings: list[SecurityFinding] = []
        sanitized_fields: list[str] = []

        if EMAIL_PATTERN.search(sanitized):
            sanitized = EMAIL_PATTERN.sub(self.redaction_placeholder, sanitized)
            findings.append(
                SecurityFinding(
                    category="EMAIL",
                    severity=SecuritySeverity.WARNING,
                    message="Email-like content was redacted from text.",
                )
            )
            sanitized_fields.append("email")

        if PHONE_PATTERN.search(sanitized):
            sanitized = PHONE_PATTERN.sub(self.redaction_placeholder, sanitized)
            findings.append(
                SecurityFinding(
                    category="PHONE",
                    severity=SecuritySeverity.WARNING,
                    message="Phone-like content was redacted from text.",
                )
            )
            sanitized_fields.append("phone")

        for marker in self.blocked_text_markers:
            if marker in sanitized:
                sanitized = sanitized.replace(marker, self.redaction_placeholder)
                findings.append(
                    SecurityFinding(
                        category="TOKEN_LIKE",
                        severity=SecuritySeverity.CRITICAL,
                        message="Token-like content was redacted from text.",
                    )
                )
                sanitized_fields.append("token_like")

        action = SecurityAction.ALLOW if not findings else SecurityAction.REDACT
        return sanitized, SecurityReviewResult(
            action=action,
            findings=findings,
            sanitized_fields=sanitized_fields,
        )

    def sanitize_mapping(self, payload: dict[str, Any]) -> tuple[dict[str, Any], SecurityReviewResult]:
        """Redact lightweight sensitive content from a mapping payload."""
        sanitized: dict[str, Any] = {}
        findings: list[SecurityFinding] = []
        sanitized_fields: list[str] = []

        for key, value in payload.items():
            lowered = key.lower()
            if any(marker in lowered for marker in self.sensitive_key_markers):
                sanitized[key] = self.redaction_placeholder
                findings.append(
                    SecurityFinding(
                        category="SENSITIVE_FIELD",
                        severity=SecuritySeverity.WARNING,
                        message=f"Field {key} matched a sensitive marker and was redacted.",
                        field_name=key,
                    )
                )
                sanitized_fields.append(key)
                continue

            if isinstance(value, str):
                sanitized_value, text_review = self.sanitize_text(value)
                sanitized[key] = sanitized_value
                findings.extend(text_review.findings)
                if text_review.requires_redaction():
                    sanitized_fields.append(key)
                continue

            sanitized[key] = value

        action = SecurityAction.ALLOW if not findings else SecurityAction.REDACT
        return sanitized, SecurityReviewResult(
            action=action,
            findings=findings,
            sanitized_fields=sanitized_fields,
        )

    def review_event_summary(self, summary: EventSummary) -> SecurityReviewResult:
        """Review runtime event summaries before they fan out further."""
        return self.sanitize_mapping(summary.payload)[1]

    def review_interrupt_signal(self, signal: InterruptSignal) -> SecurityReviewResult:
        """Review interrupt signals before they are exposed to platform services."""
        return self._merge_reviews(
            [
                self.sanitize_text(signal.reason)[1],
                self.sanitize_mapping(signal.payload)[1],
            ]
        )

    def review_runtime_snapshot(self, snapshot: RuntimeSnapshot) -> SecurityReviewResult:
        """Review runtime snapshots before they are persisted or observed."""
        return self.sanitize_mapping(snapshot.payload)[1]

    @staticmethod
    def _merge_reviews(reviews: Iterable[SecurityReviewResult]) -> SecurityReviewResult:
        """Merge multiple review results into one typed outcome."""
        findings: list[SecurityFinding] = []
        sanitized_fields: list[str] = []
        action = SecurityAction.ALLOW

        for review in reviews:
            findings.extend(review.findings)
            for field_name in review.sanitized_fields:
                if field_name not in sanitized_fields:
                    sanitized_fields.append(field_name)
            if review.action is SecurityAction.BLOCK:
                action = SecurityAction.BLOCK
            elif review.action is SecurityAction.REDACT and action is SecurityAction.ALLOW:
                action = SecurityAction.REDACT

        return SecurityReviewResult(
            action=action,
            findings=findings,
            sanitized_fields=sanitized_fields,
        )
