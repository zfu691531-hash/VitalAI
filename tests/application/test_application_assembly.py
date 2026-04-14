"""Tests for the lightweight application composition layer."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from VitalAI.application import (
    ApplicationAssembly,
    ApplicationAssemblyConfig,
    ApplicationAssemblyPolicySnapshot,
    ApplicationRuntimeDiagnostics,
    build_application_assembly_for_role,
    build_application_assembly_from_environment,
    build_application_assembly_from_environment_for_role,
    build_daily_life_workflow,
    build_health_workflow,
    build_mental_care_workflow,
)
from VitalAI.application.commands import (
    DailyLifeCheckInCommand,
    HealthAlertCommand,
    MentalCareCheckInCommand,
)
from VitalAI.domains.reporting import FeedbackReport, FeedbackReportRequest, FeedbackReportService
from VitalAI.platform.messaging import MessageEnvelope


class StubFeedbackReportService(FeedbackReportService):
    """Simple stub report service used to verify configurable assembly."""

    def build_report(self, request: FeedbackReportRequest) -> FeedbackReport:
        return FeedbackReport(
            trace_id=request.trace_id,
            title=f"stub:{request.agent_id}",
            body=f"stub:{request.summary}",
        )


class ApplicationAssemblyTests(unittest.TestCase):
    def test_build_health_workflow_returns_executable_workflow(self) -> None:
        workflow = build_health_workflow()
        result = workflow.run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-1",
                user_id="elder-1201",
                risk_level="high",
            )
        )

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertEqual(2, len(result.flow_result.runtime_observations))
        self.assertEqual(2, len(result.runtime_signals))

    def test_build_daily_life_workflow_returns_executable_workflow(self) -> None:
        workflow = build_daily_life_workflow()
        result = workflow.run(
            DailyLifeCheckInCommand(
                source_agent="assembly-daily",
                trace_id="trace-assembly-daily-1",
                user_id="elder-1202",
                need="meal_support",
                urgency="normal",
            )
        )

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertEqual(2, len(result.flow_result.runtime_observations))
        self.assertEqual(2, len(result.runtime_signals))

    def test_build_mental_care_workflow_returns_executable_workflow(self) -> None:
        workflow = build_mental_care_workflow()
        result = workflow.run(
            MentalCareCheckInCommand(
                source_agent="assembly-mental",
                trace_id="trace-assembly-mental-1",
                user_id="elder-1203",
                mood_signal="distressed",
                support_need="emotional_checkin",
            )
        )

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertEqual(2, len(result.flow_result.runtime_observations))
        self.assertEqual(2, len(result.runtime_signals))

    def test_custom_report_service_can_be_injected_via_config(self) -> None:
        config = ApplicationAssemblyConfig(
            feedback_report_service_factory=StubFeedbackReportService,
        )
        workflow = build_health_workflow(config=config)

        result = workflow.run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-2",
                user_id="elder-1204",
                risk_level="critical",
            )
        )

        self.assertIsNotNone(result.feedback_report)
        self.assertTrue(result.feedback_report.title.startswith("stub:"))

    def test_environment_can_disable_reporting_for_default_assembly(self) -> None:
        with patch.dict("os.environ", {"APP_ENV": "testing", "VITALAI_REPORTING_ENABLED": "false"}):
            assembly = build_application_assembly_from_environment()

        self.assertIsInstance(assembly, ApplicationAssembly)
        self.assertIsNotNone(assembly.environment)
        self.assertEqual("testing", assembly.environment.app_env)
        self.assertFalse(assembly.environment.reporting_enabled)
        self.assertTrue(assembly.environment.runtime_signals_enabled)

        result = assembly.build_health_workflow().run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-3",
                user_id="elder-1205",
                risk_level="high",
            )
        )

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNone(result.feedback_report)

    def test_environment_role_can_be_resolved_explicitly(self) -> None:
        with patch.dict("os.environ", {"APP_ENV": "testing", "VITALAI_RUNTIME_ROLE": "ignored-role"}):
            assembly = build_application_assembly_from_environment_for_role("scheduler")

        self.assertEqual("scheduler", assembly.runtime_role)
        self.assertIsNotNone(assembly.environment)
        self.assertEqual("scheduler", assembly.environment.runtime_role)
        self.assertFalse(assembly.environment.reporting_enabled)
        self.assertFalse(assembly.environment.runtime_signals_enabled)

    def test_role_builder_keeps_role_metadata_when_config_is_injected(self) -> None:
        config = ApplicationAssemblyConfig(
            feedback_report_service_factory=StubFeedbackReportService,
        )
        assembly = build_application_assembly_for_role("consumer", config=config)

        self.assertEqual("consumer", assembly.runtime_role)
        self.assertIsNotNone(assembly.environment)
        self.assertEqual("consumer", assembly.environment.runtime_role)

    def test_scheduler_role_disables_reporting_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            assembly = build_application_assembly_from_environment_for_role("scheduler")

        result = assembly.build_health_workflow().run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-4",
                user_id="elder-1206",
                risk_level="high",
            )
        )

        self.assertFalse(assembly.environment is None)
        self.assertFalse(assembly.environment.reporting_enabled)
        self.assertIsNone(result.feedback_report)
        self.assertEqual([], result.runtime_signals)

    def test_scheduler_role_disables_ack_on_ingress_messages(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("scheduler")
        envelope = MessageEnvelope(
            from_agent="scheduler",
            to_agent="decision-core",
            trace_id="trace-assembly-ack-1",
            payload={"kind": "scheduled"},
            msg_type="HEALTH_ALERT",
            require_ack=True,
        )

        adjusted = assembly.apply_ingress_policy(envelope)

        self.assertFalse(adjusted.require_ack)
        self.assertEqual(300, adjusted.ttl)

    def test_consumer_role_enforces_ack_on_ingress_messages(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("consumer")
        envelope = MessageEnvelope(
            from_agent="consumer",
            to_agent="decision-core",
            trace_id="trace-assembly-ack-2",
            payload={"kind": "consumed"},
            msg_type="HEALTH_ALERT",
            require_ack=False,
        )

        adjusted = assembly.apply_ingress_policy(envelope)

        self.assertTrue(adjusted.require_ack)
        self.assertEqual(60, adjusted.ttl)

    def test_api_role_preserves_command_level_ttl_defaults(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")
        envelope = MessageEnvelope(
            from_agent="api",
            to_agent="decision-core",
            trace_id="trace-assembly-ttl-1",
            payload={"kind": "api"},
            msg_type="HEALTH_ALERT",
            ttl=30,
            require_ack=True,
        )

        adjusted = assembly.apply_ingress_policy(envelope)

        self.assertEqual(30, adjusted.ttl)
        self.assertTrue(adjusted.require_ack)

    def test_policy_snapshot_exposes_active_role_policies(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("scheduler")

        snapshot = assembly.describe_policies()

        self.assertIsInstance(snapshot, ApplicationAssemblyPolicySnapshot)
        self.assertEqual("scheduler", snapshot.runtime_role)
        self.assertFalse(snapshot.reporting_enabled)
        self.assertEqual("role_default", snapshot.reporting_policy_source)
        self.assertFalse(snapshot.runtime_signals_enabled)
        self.assertEqual("role_default", snapshot.runtime_signals_policy_source)
        self.assertFalse(snapshot.require_ack_override)
        self.assertEqual(300, snapshot.ttl_override)
        self.assertEqual("role_default", snapshot.ingress_policy_source)

    def test_environment_can_disable_runtime_signal_bridge(self) -> None:
        with patch.dict("os.environ", {"VITALAI_RUNTIME_SIGNALS_ENABLED": "false"}):
            assembly = build_application_assembly_from_environment_for_role("api")

        result = assembly.build_health_workflow().run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-6",
                user_id="elder-1208",
                risk_level="high",
            )
        )

        self.assertFalse(assembly.environment is None)
        self.assertFalse(assembly.environment.runtime_signals_enabled)
        self.assertEqual([], result.runtime_signals)

    def test_runtime_diagnostics_emit_snapshot_and_failover_signals(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")

        diagnostics = assembly.run_runtime_diagnostics()

        self.assertIsInstance(diagnostics, ApplicationRuntimeDiagnostics)
        self.assertEqual("api", diagnostics.runtime_role)
        self.assertEqual("api-runtime-snapshot", diagnostics.snapshot_id)
        self.assertTrue(diagnostics.failover_triggered)
        self.assertEqual("shadow", diagnostics.active_node)
        self.assertIsNone(diagnostics.interrupt_action)
        self.assertIsNone(diagnostics.interrupt_has_snapshot_refs)
        self.assertEqual("ALLOW", diagnostics.latest_security_action)
        self.assertEqual(0, diagnostics.latest_security_finding_count)
        self.assertEqual("INFO", diagnostics.latest_security_highest_severity)
        self.assertIsNotNone(diagnostics.latest_failover_signal_id)
        self.assertEqual(3, len(diagnostics.runtime_signals))
        self.assertEqual("RUNTIME_SNAPSHOT", diagnostics.runtime_signals[0].kind)
        self.assertEqual("SECURITY_REVIEW", diagnostics.runtime_signals[1].kind)
        self.assertEqual("FAILOVER_TRANSITION", diagnostics.runtime_signals[2].kind)
        self.assertTrue(diagnostics.runtime_signals[2].details["has_snapshot_refs"])
        self.assertEqual(["api-runtime-snapshot"], diagnostics.runtime_signals[2].details["snapshot_ids"])

    def test_runtime_diagnostics_respect_runtime_signal_policy(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("scheduler")

        diagnostics = assembly.run_runtime_diagnostics()

        self.assertEqual("scheduler", diagnostics.runtime_role)
        self.assertEqual("scheduler-runtime-snapshot", diagnostics.snapshot_id)
        self.assertTrue(diagnostics.failover_triggered)
        self.assertEqual("shadow", diagnostics.active_node)
        self.assertIsNone(diagnostics.interrupt_action)
        self.assertIsNone(diagnostics.interrupt_has_snapshot_refs)
        self.assertIsNone(diagnostics.latest_security_action)
        self.assertIsNone(diagnostics.latest_security_finding_count)
        self.assertIsNone(diagnostics.latest_security_highest_severity)
        self.assertIsNone(diagnostics.latest_failover_signal_id)
        self.assertEqual([], diagnostics.runtime_signals)

    def test_health_critical_failover_drill_uses_real_flow_interrupt_before_failover(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("api")

        diagnostics = assembly.run_health_critical_failover_drill()

        self.assertEqual("api", diagnostics.runtime_role)
        self.assertTrue(diagnostics.failover_triggered)
        self.assertEqual("shadow", diagnostics.active_node)
        self.assertIsNotNone(diagnostics.snapshot_id)
        self.assertEqual("TAKEOVER", diagnostics.interrupt_action)
        self.assertTrue(diagnostics.interrupt_has_snapshot_refs)
        self.assertEqual("ALLOW", diagnostics.latest_security_action)
        self.assertEqual(0, diagnostics.latest_security_finding_count)
        self.assertEqual("INFO", diagnostics.latest_security_highest_severity)
        self.assertIsNotNone(diagnostics.latest_failover_signal_id)
        self.assertEqual(7, len(diagnostics.runtime_signals))
        self.assertEqual("EVENT_SUMMARY", diagnostics.runtime_signals[0].kind)
        self.assertEqual("RUNTIME_SNAPSHOT", diagnostics.runtime_signals[2].kind)
        self.assertEqual("INTERRUPT_SIGNAL", diagnostics.runtime_signals[4].kind)
        self.assertTrue(diagnostics.runtime_signals[4].details["has_snapshot_refs"])
        self.assertEqual("FAILOVER_TRANSITION", diagnostics.runtime_signals[6].kind)
        self.assertTrue(diagnostics.runtime_signals[6].details["has_snapshot_refs"])
        self.assertEqual([diagnostics.snapshot_id], diagnostics.runtime_signals[6].details["snapshot_ids"])

    def test_health_critical_failover_drill_respects_runtime_signal_policy(self) -> None:
        assembly = build_application_assembly_from_environment_for_role("scheduler")

        diagnostics = assembly.run_health_critical_failover_drill()

        self.assertEqual("scheduler", diagnostics.runtime_role)
        self.assertIsNone(diagnostics.snapshot_id)
        self.assertFalse(diagnostics.failover_triggered)
        self.assertEqual("primary", diagnostics.active_node)
        self.assertIsNone(diagnostics.interrupt_action)
        self.assertIsNone(diagnostics.interrupt_has_snapshot_refs)
        self.assertIsNone(diagnostics.latest_security_action)
        self.assertIsNone(diagnostics.latest_security_finding_count)
        self.assertIsNone(diagnostics.latest_security_highest_severity)
        self.assertIsNone(diagnostics.latest_failover_signal_id)
        self.assertEqual([], diagnostics.runtime_signals)

    def test_scheduler_role_can_explicitly_enable_reporting(self) -> None:
        with patch.dict("os.environ", {"VITALAI_REPORTING_ENABLED": "true"}):
            assembly = build_application_assembly_from_environment_for_role("scheduler")
            snapshot = assembly.describe_policies()

        result = assembly.build_health_workflow().run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-5",
                user_id="elder-1207",
                risk_level="critical",
            )
        )

        self.assertFalse(assembly.environment is None)
        self.assertTrue(assembly.environment.reporting_enabled)
        self.assertIsNotNone(result.feedback_report)
        self.assertEqual("environment_override", snapshot.reporting_policy_source)

    def test_scheduler_role_can_explicitly_enable_runtime_signals(self) -> None:
        with patch.dict("os.environ", {"VITALAI_RUNTIME_SIGNALS_ENABLED": "true"}):
            assembly = build_application_assembly_from_environment_for_role("scheduler")
            snapshot = assembly.describe_policies()

        result = assembly.build_health_workflow().run(
            HealthAlertCommand(
                source_agent="assembly-health",
                trace_id="trace-assembly-health-7",
                user_id="elder-1209",
                risk_level="critical",
            )
        )

        self.assertFalse(assembly.environment is None)
        self.assertTrue(assembly.environment.runtime_signals_enabled)
        self.assertEqual(6, len(result.runtime_signals))
        self.assertEqual("environment_override", snapshot.runtime_signals_policy_source)


if __name__ == "__main__":
    unittest.main()
