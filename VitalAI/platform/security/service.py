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
# Avoid matching digit runs embedded inside technical identifiers such as hex-like ids.
PHONE_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:1\d{10}|(?:\+?\d[\d -]{8,}\d))(?![A-Za-z0-9])")


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
    technical_identifier_fields: tuple[str, ...] = (
        "message_id",
        "trace_id",
        "signal_id",
        "snapshot_id",
        "event_id",
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
        return self._sanitize_mapping(payload, field_path="")

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

    def _sanitize_mapping(
        self,
        payload: dict[str, Any],
        *,
        field_path: str,
    ) -> tuple[dict[str, Any], SecurityReviewResult]:
        """Recursively sanitize one mapping while preserving field-level paths."""
        sanitized: dict[str, Any] = {}
        findings: list[SecurityFinding] = []
        sanitized_fields: list[str] = []

        for key, value in payload.items():
            lowered = key.lower()
            nested_path = key if field_path == "" else f"{field_path}.{key}"
            if any(marker in lowered for marker in self.sensitive_key_markers):
                sanitized[key] = self.redaction_placeholder
                findings.append(
                    SecurityFinding(
                        category="SENSITIVE_FIELD",
                        severity=SecuritySeverity.WARNING,
                        message=f"Field {nested_path} matched a sensitive marker and was redacted.",
                        field_name=nested_path,
                    )
                )
                sanitized_fields.append(nested_path)
                continue

            sanitized_value, review = self._sanitize_value(
                value,
                field_path=nested_path,
                field_name=lowered,
            )
            sanitized[key] = sanitized_value
            findings.extend(review.findings)
            sanitized_fields.extend(review.sanitized_fields)

        return sanitized, self._build_review(findings, sanitized_fields)

    def _sanitize_sequence(
        self,
        values: list[Any] | tuple[Any, ...],
        *,
        field_path: str,
    ) -> tuple[list[Any] | tuple[Any, ...], SecurityReviewResult]:
        """Recursively sanitize sequence items and preserve their positions."""
        sanitized_items: list[Any] = []
        findings: list[SecurityFinding] = []
        sanitized_fields: list[str] = []

        for index, item in enumerate(values):
            item_path = f"{field_path}[{index}]"
            sanitized_item, review = self._sanitize_value(item, field_path=item_path, field_name=None)
            sanitized_items.append(sanitized_item)
            findings.extend(review.findings)
            sanitized_fields.extend(review.sanitized_fields)

        sanitized_sequence: list[Any] | tuple[Any, ...] = sanitized_items
        if isinstance(values, tuple):
            sanitized_sequence = tuple(sanitized_items)
        return sanitized_sequence, self._build_review(findings, sanitized_fields)

    def _sanitize_value(
        self,
        value: Any,
        *,
        field_path: str,
        field_name: str | None,
    ) -> tuple[Any, SecurityReviewResult]:
        """Sanitize one arbitrary runtime value and scope findings to its field path."""
        if isinstance(value, dict):
            return self._sanitize_mapping(value, field_path=field_path)
        if isinstance(value, list | tuple):
            return self._sanitize_sequence(value, field_path=field_path)
        if isinstance(value, str):
            if field_name in self.technical_identifier_fields:
                return value, SecurityReviewResult(action=SecurityAction.ALLOW)
            sanitized_text, review = self.sanitize_text(value)
            return sanitized_text, self._scope_review(review, field_path)
        return value, SecurityReviewResult(action=SecurityAction.ALLOW)

    @staticmethod
    def _build_review(
        findings: list[SecurityFinding],
        sanitized_fields: list[str],
    ) -> SecurityReviewResult:
        """Build one review result from accumulated findings and field paths."""
        deduped_fields: list[str] = []
        for field_name in sanitized_fields:
            if field_name not in deduped_fields:
                deduped_fields.append(field_name)
        action = SecurityAction.ALLOW if not findings else SecurityAction.REDACT
        return SecurityReviewResult(
            action=action,
            findings=findings,
            sanitized_fields=deduped_fields,
        )

    @staticmethod
    def _scope_review(review: SecurityReviewResult, field_path: str) -> SecurityReviewResult:
        """Translate generic text findings into one concrete field path."""
        if not review.requires_redaction():
            return review
        findings = [
            SecurityFinding(
                category=finding.category,
                severity=finding.severity,
                message=finding.message,
                field_name=field_path if finding.field_name is None else finding.field_name,
            )
            for finding in review.findings
        ]
        return SecurityReviewResult(
            action=review.action,
            findings=findings,
            sanitized_fields=[field_path],
        )

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
