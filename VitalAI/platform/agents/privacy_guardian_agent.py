"""Privacy guardian scaffold backed by the shared security guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from VitalAI.platform.agents.agent_contract import (
    AgentCycleTrace,
    AgentDecision,
    AgentDescriptor,
    AgentDryRunResult,
    AgentExecution,
    AgentExecutionResult,
    AgentPerception,
)
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority
from VitalAI.platform.security import SecurityReviewResult, SensitiveDataGuard


@dataclass(slots=True)
class PrivacyGuardianReviewOutput:
    """Typed result for one privacy review cycle."""

    review_payload: dict[str, Any]
    sanitized_payload: dict[str, Any]
    review: SecurityReviewResult
    envelope: MessageEnvelope


@dataclass(slots=True)
class PrivacyGuardianAgent:
    """Run lightweight redaction and security review before data leaves the system."""

    security_guard: SensitiveDataGuard = field(default_factory=SensitiveDataGuard)
    agent_id: str = "privacy-guardian-agent"

    def describe(self) -> AgentDescriptor:
        """Return a stable registry descriptor for the privacy guardian."""
        return AgentDescriptor(
            agent_id=self.agent_id,
            display_name="Privacy Guardian Agent",
            layer="platform",
            domain="security",
            status="framework_ready",
            summary="负责脱敏、输出审查和出境前隐私过滤，当前提供 dry-run 审查接口。",
            execution_mode="security_review",
            accepts=("security_review", "redaction_preview"),
            emits=("security_review_result", "sanitized_payload"),
            platform_bindings=("messaging", "security_review"),
        )

    def dry_run(self, payload: dict[str, Any]) -> AgentDryRunResult:
        """Preview one privacy/security review using the shared guard."""
        source_agent = _payload_text(payload, "source_agent", "agent-registry-api")
        review_payload = _payload_mapping(payload.get("payload"))
        if not review_payload:
            review_payload = {
                "text": _payload_text(payload, "text", _payload_text(payload, "message", "")),
            }
        execution_result = self.review_payload_cycle(
            source_agent=source_agent,
            review_payload=review_payload,
            dry_run=True,
        )
        review_output = execution_result.result
        review = review_output.review
        return AgentDryRunResult(
            agent_id=self.agent_id,
            accepted=True,
            summary=f"Privacy guardian reviewed payload with action {review.action.value}.",
            execution_mode="security_review",
            preview={
                "action": review.action.value,
                "sanitized_fields": list(review.sanitized_fields),
                "highest_severity": review.highest_severity().value,
                "sanitized_payload": review_output.sanitized_payload,
            },
            envelope=review_output.envelope,
            cycle=execution_result.cycle,
            findings=_findings_payload(review),
            notes=[
                "This preview uses the same SensitiveDataGuard that already protects reporting and runtime views.",
            ],
        )

    def review_payload_cycle(
        self,
        *,
        source_agent: str,
        review_payload: dict[str, Any],
        dry_run: bool = False,
    ) -> AgentExecutionResult:
        """Run one reusable privacy-review cycle that other agents can call."""
        perception = AgentPerception(
            summary="Privacy guardian inspected one payload for sensitive fields and risky text.",
            signals={
                "source_agent": source_agent,
                "payload_keys": list(review_payload.keys()),
            },
        )
        sanitized_payload, review = self.security_guard.sanitize_mapping(review_payload)
        decision = AgentDecision(
            decision_type="security_review",
            summary=f"Privacy guardian chose {review.action.value} for the inspected payload.",
            rationale="Outbound data should be redacted before leaving the system when sensitive patterns are present.",
            payload={
                "action": review.action.value,
                "sanitized_fields": list(review.sanitized_fields),
                "highest_severity": review.highest_severity().value,
            },
        )
        envelope = MessageEnvelope(
            from_agent=source_agent,
            to_agent=self.agent_id,
            payload={"review_payload": review_payload, "dry_run": dry_run},
            msg_type="SECURITY_REVIEW",
            priority=MessagePriority.HIGH,
            require_ack=True,
        )
        execution = AgentExecution(
            action="emit_security_review_result",
            status=review.action.value.lower(),
            summary="Privacy guardian produced one sanitized payload preview.",
            payload={
                "sanitized_fields": list(review.sanitized_fields),
                "finding_count": len(review.findings),
                "highest_severity": review.highest_severity().value,
            },
        )
        return AgentExecutionResult(
            result=PrivacyGuardianReviewOutput(
                review_payload=dict(review_payload),
                sanitized_payload=sanitized_payload,
                review=review,
                envelope=envelope,
            ),
            cycle=AgentCycleTrace(
                agent_id=self.agent_id,
                perception=perception,
                decision=decision,
                execution=execution,
            ),
        )


def _payload_text(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return default if text == "" else text


def _payload_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _findings_payload(review: SecurityReviewResult) -> list[dict[str, Any]]:
    return [
        {
            "category": finding.category,
            "severity": finding.severity.value,
            "message": finding.message,
            "field_name": finding.field_name,
        }
        for finding in review.findings
    ]
