"""Typed security review results used by the platform security layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SecurityAction(StrEnum):
    """Recommended action after one security review."""

    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


class SecuritySeverity(StrEnum):
    """Severity level attached to one security finding."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class SecurityFinding:
    """One concrete security finding."""

    category: str
    severity: SecuritySeverity
    message: str
    field_name: str | None = None


@dataclass(slots=True)
class SecurityReviewResult:
    """Typed result produced by one security review."""

    action: SecurityAction
    findings: list[SecurityFinding] = field(default_factory=list)
    sanitized_fields: list[str] = field(default_factory=list)

    def requires_redaction(self) -> bool:
        """Return whether this review requires redaction or blocking."""
        return self.action in {SecurityAction.REDACT, SecurityAction.BLOCK}

    def highest_severity(self) -> SecuritySeverity:
        """Return the highest severity found in this review."""
        if not self.findings:
            return SecuritySeverity.INFO
        if any(finding.severity is SecuritySeverity.CRITICAL for finding in self.findings):
            return SecuritySeverity.CRITICAL
        if any(finding.severity is SecuritySeverity.WARNING for finding in self.findings):
            return SecuritySeverity.WARNING
        return SecuritySeverity.INFO
