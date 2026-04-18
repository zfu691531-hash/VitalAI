"""Intelligent reporting agent scaffold backed by tool-agent collaboration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from VitalAI.platform.agents.agent_contract import (
    AgentCycleTrace,
    AgentDecision,
    AgentDescriptor,
    AgentDryRunResult,
    AgentExecution,
    AgentPerception,
)
from VitalAI.platform.agents.privacy_guardian_agent import PrivacyGuardianAgent
from VitalAI.platform.agents.tool_agent import ToolAgent
from VitalAI.platform.messaging import MessageEnvelope, MessagePriority


@dataclass(slots=True)
class IntelligentReportingAgent:
    """Generate a lightweight reporting preview by collaborating with tool-agent."""

    tool_agent: ToolAgent
    privacy_guardian_agent: PrivacyGuardianAgent
    agent_id: str = "intelligent-reporting-agent"

    def describe(self) -> AgentDescriptor:
        """Return a registry descriptor for the reporting agent."""
        return AgentDescriptor(
            agent_id=self.agent_id,
            display_name="Intelligent Reporting Agent",
            layer="domain",
            domain="reporting",
            status="framework_ready",
            summary="Uses tool-agent to fetch a cross-domain overview, then builds a read-only report preview and sends it through privacy review.",
            execution_mode="read_only_report_preview",
            accepts=("report_request", "overview_summary"),
            emits=("report_preview", "attention_summary"),
            platform_bindings=("messaging", "tool_agent", "security_review"),
        )

    def dry_run(
        self,
        *,
        user_id: str,
        source_agent: str,
        trace_id: str,
        history_limit: int = 3,
        memory_key: str = "",
    ) -> AgentDryRunResult:
        """Build one dry-run report preview through tool-agent and privacy review."""
        return self.generate_report_preview(
            user_id=user_id,
            source_agent=source_agent,
            trace_id=trace_id,
            history_limit=history_limit,
            memory_key=memory_key,
            dry_run=True,
        )

    def generate_report_preview(
        self,
        *,
        user_id: str,
        source_agent: str,
        trace_id: str,
        history_limit: int = 3,
        memory_key: str = "",
        dry_run: bool = False,
    ) -> AgentDryRunResult:
        """Build one read-only report preview through tool-agent and privacy review."""
        overview_lookup = self.tool_agent.run_tool_cycle(
            source_agent=self.agent_id,
            tool_name="user_overview_lookup",
            params={
                "user_id": user_id,
                "history_limit": history_limit,
                "memory_key": memory_key,
            },
            trace_id=f"{trace_id}:overview_lookup",
            dry_run=dry_run,
        )
        tool_output = overview_lookup.result
        overview = dict(tool_output.result)
        overview_accepted = bool(overview.get("accepted"))
        recent_activity = _as_list(overview.get("recent_activity"))
        attention_items = _as_list(overview.get("attention_items"))
        perception = AgentPerception(
            summary="Reporting agent requested one overview lookup from tool-agent and inspected the returned activity and attention hints.",
            signals={
                "user_id": user_id,
                "history_limit": history_limit,
                "overview_lookup_agent_id": self.tool_agent.agent_id,
                "overview_lookup_execution_mode": tool_output.execution_mode,
                "latest_activity_at": overview.get("latest_activity_at"),
                "attention_count": len(attention_items),
            },
        )
        decision = AgentDecision(
            decision_type="generate_overview_report_preview",
            summary="Generate one read-only reporting preview from the overview returned by tool-agent.",
            rationale="The reporting agent should collaborate with the central tool gateway for cross-domain reads, while keeping report generation and outbound review inside the reporting path.",
            payload={
                "attention_summary": overview.get("attention_summary"),
                "recent_activity_count": len(recent_activity),
                "overview_lookup_agent_id": self.tool_agent.agent_id,
                "overview_lookup_tool_name": tool_output.tool_name,
                "security_review_agent_id": self.privacy_guardian_agent.agent_id,
            },
        )
        report_preview = {
            "title": f"{user_id} overview report",
            "body": _build_report_body(overview),
            "latest_activity_at": overview.get("latest_activity_at"),
            "attention_summary": overview.get("attention_summary"),
            "attention_count": len(attention_items),
            "source_lookup": {
                "collaborator_agent_id": self.tool_agent.agent_id,
                "tool_name": tool_output.tool_name,
                "execution_mode": tool_output.execution_mode,
                "accepted": overview_accepted,
                "recent_activity_count": len(recent_activity),
                "attention_count": len(attention_items),
                "cycle": asdict(overview_lookup.cycle),
            },
        }
        privacy_execution_result = self.privacy_guardian_agent.review_payload_cycle(
            source_agent=self.agent_id,
            review_payload=report_preview,
            dry_run=True,
        )
        privacy_review = privacy_execution_result.result.review
        sanitized_preview = dict(privacy_execution_result.result.sanitized_payload)
        envelope = MessageEnvelope(
            from_agent=source_agent,
            to_agent=self.agent_id,
            payload={
                "user_id": user_id,
                "history_limit": history_limit,
                "memory_key": memory_key,
                "dry_run": dry_run,
            },
            msg_type="REPORT_REQUEST",
            priority=MessagePriority.NORMAL,
        )
        execution = AgentExecution(
            action="emit_report_preview",
            status="accepted" if overview_accepted else "degraded",
            summary="Reporting agent emitted one sanitized report preview.",
            payload={
                "attention_count": len(attention_items),
                "overview_lookup_agent_id": self.tool_agent.agent_id,
                "overview_lookup_execution_mode": tool_output.execution_mode,
                "finding_count": len(privacy_review.findings),
                "security_review_action": privacy_review.action.value,
                "security_review_agent_id": self.privacy_guardian_agent.agent_id,
            },
        )
        return AgentDryRunResult(
            agent_id=self.agent_id,
            accepted=overview_accepted,
            summary="Intelligent reporting agent generated a read-only report preview through tool-agent.",
            execution_mode="read_only_report_preview",
            preview={
                **sanitized_preview,
                "security_review": {
                    "reviewer_agent_id": self.privacy_guardian_agent.agent_id,
                    "action": privacy_review.action.value,
                    "sanitized_fields": list(privacy_review.sanitized_fields),
                    "highest_severity": privacy_review.highest_severity().value,
                },
            },
            envelope=envelope,
            cycle=AgentCycleTrace(
                agent_id=self.agent_id,
                perception=perception,
                decision=decision,
                execution=execution,
            ),
            findings=[
                {
                    "category": finding.category,
                    "severity": finding.severity.value,
                    "message": finding.message,
                    "field_name": finding.field_name,
                }
                for finding in privacy_review.findings
            ],
            notes=[
                "This preview is read-only and loads the overview through tool-agent.",
                "Privacy guardian reviewed the outbound report preview before exposure.",
            ],
        )


def _build_report_body(result: dict[str, Any]) -> str:
    attention_summary = str(result.get("attention_summary") or "No attention summary.")
    recent_activity = _as_list(result.get("recent_activity"))
    latest_activity_at = str(result.get("latest_activity_at") or "")
    activity_domains = [str(item.get("domain", "")) for item in recent_activity[:3]]
    joined_domains = ", ".join(domain for domain in activity_domains if domain) or "no recent domains"
    return (
        f"latest_activity_at={latest_activity_at}; "
        f"attention={attention_summary}; "
        f"recent_domains={joined_domains}"
    )


def _as_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
