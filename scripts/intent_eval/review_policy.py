"""Review policy helpers for second-layer snapshot triage."""

from __future__ import annotations

from typing import Any


APPROVE_CANDIDATE = "approve_candidate"
MANUAL_REVIEW_REQUIRED = "manual_review_required"
BASELINE_NEGATIVE_CANDIDATE = "baseline_negative_candidate"

ELIGIBLE_FOR_BULK_APPROVAL = "eligible_for_bulk_approval"
REQUIRES_MANUAL_APPROVAL = "requires_manual_approval"
NOT_APPLICABLE_FOR_BULK_APPROVAL = "not_applicable_for_bulk_approval"

_SAFE_BULK_PRIMARY_INTENTS = {
    "profile_memory_update",
    "profile_memory_query",
    "daily_life_checkin",
}


def suggest_review_recommendation(record: dict[str, Any]) -> tuple[str, list[str]]:
    """Classify one captured snapshot into a review recommendation bucket."""
    parse_error = record.get("parse_error")
    if isinstance(parse_error, str) and parse_error.strip():
        return (
            BASELINE_NEGATIVE_CANDIDATE,
            ["parse_error"],
        )

    validation = record.get("validation")
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        issue_codes: list[str] = []
        if isinstance(validation, dict):
            for issue in validation.get("issues", []):
                if isinstance(issue, dict):
                    code = issue.get("code")
                    if isinstance(code, str) and code:
                        issue_codes.append(f"issue_code:{code}")
        reasons = ["validation_invalid"]
        reasons.extend(issue_codes)
        return (BASELINE_NEGATIVE_CANDIDATE, reasons)

    guard = record.get("guard") or {}
    guard_status = str(guard.get("status", "")).strip() or "unknown"
    blocked_reasons = [
        str(reason)
        for reason in (guard.get("blocked_reasons") or [])
        if str(reason).strip()
    ]
    if guard_status in {"routing_candidate", "clarification_candidate", "rejected_by_second_layer"}:
        return (
            APPROVE_CANDIDATE,
            [f"guard_status:{guard_status}"],
        )

    reasons = [f"guard_status:{guard_status}"]
    reasons.extend(f"blocked_reason:{reason}" for reason in blocked_reasons)
    return (MANUAL_REVIEW_REQUIRED, reasons)


def suggest_bulk_approval_recommendation(
    record: dict[str, Any],
    *,
    review_recommendation: str | None = None,
) -> tuple[str, list[str]]:
    """Classify whether one queue candidate is safe for bulk approval."""
    recommendation = (
        review_recommendation.strip()
        if isinstance(review_recommendation, str) and review_recommendation.strip()
        else suggest_review_recommendation(record)[0]
    )
    if recommendation != APPROVE_CANDIDATE:
        return (
            NOT_APPLICABLE_FOR_BULK_APPROVAL,
            [f"review_recommendation:{recommendation}"],
        )

    validation = record.get("validation")
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        return (
            REQUIRES_MANUAL_APPROVAL,
            ["validation_not_confirmed"],
        )

    validation_result = validation.get("result") or {}
    if not isinstance(validation_result, dict):
        validation_result = {}
    risk_flags = validation_result.get("risk_flags") or []
    risk_kinds: list[str] = []
    if isinstance(risk_flags, list):
        for risk_flag in risk_flags:
            if isinstance(risk_flag, dict):
                kind = str(risk_flag.get("kind", "")).strip()
                if kind:
                    risk_kinds.append(kind)

    guard = record.get("guard") or {}
    guard_status = str(guard.get("status", "")).strip()
    if guard_status == "clarification_candidate":
        if risk_kinds:
            return (
                REQUIRES_MANUAL_APPROVAL,
                ["guard_status:clarification_candidate", "risk_flags_present"]
                + [f"risk_flag:{kind}" for kind in risk_kinds],
            )
        return (
            ELIGIBLE_FOR_BULK_APPROVAL,
            [f"guard_status:{guard_status}"],
        )
    if guard_status == "rejected_by_second_layer":
        return (
            ELIGIBLE_FOR_BULK_APPROVAL,
            [f"guard_status:{guard_status}"],
        )
    if guard_status != "routing_candidate":
        return (
            REQUIRES_MANUAL_APPROVAL,
            [f"guard_status:{guard_status or 'unknown'}"],
        )

    if not isinstance(validation_result, dict):
        return (
            REQUIRES_MANUAL_APPROVAL,
            ["missing_validation_result"],
        )
    if risk_kinds:
        reasons = ["risk_flags_present"]
        reasons.extend(f"risk_flag:{kind}" for kind in risk_kinds)
        return (REQUIRES_MANUAL_APPROVAL, reasons)

    routing_candidate = guard.get("routing_candidate") or {}
    if not isinstance(routing_candidate, dict):
        return (
            REQUIRES_MANUAL_APPROVAL,
            ["missing_routing_candidate"],
        )

    routing_decision = str(routing_candidate.get("routing_decision", "")).strip()
    if routing_decision != "route_primary":
        return (
            REQUIRES_MANUAL_APPROVAL,
            [f"routing_decision:{routing_decision or 'unknown'}"],
        )

    primary_intent = str(routing_candidate.get("intent", "")).strip()
    if primary_intent not in _SAFE_BULK_PRIMARY_INTENTS:
        return (
            REQUIRES_MANUAL_APPROVAL,
            [f"primary_intent:{primary_intent or 'unknown'}"],
        )

    secondary_intents = [
        str(intent).strip()
        for intent in (routing_candidate.get("secondary_intents") or [])
        if str(intent).strip()
    ]
    if secondary_intents:
        return (
            REQUIRES_MANUAL_APPROVAL,
            ["secondary_intents_present"] + [f"secondary_intent:{intent}" for intent in secondary_intents],
        )

    confidence = routing_candidate.get("confidence")
    if not isinstance(confidence, (int, float)) or float(confidence) < 0.85:
        return (
            REQUIRES_MANUAL_APPROVAL,
            [f"confidence:{confidence!r}"],
        )

    return (
        ELIGIBLE_FOR_BULK_APPROVAL,
        [f"primary_intent:{primary_intent}", f"confidence:{float(confidence):.2f}"],
    )
