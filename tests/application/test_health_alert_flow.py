"""Tests for the current application-facing typed flows."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from VitalAI.application import (
    DailyLifeCheckInCommand,
    DailyLifeCheckInWorkflow,
    HealthAlertCommand,
    HealthAlertWorkflow,
    RunDailyLifeCheckInFlowUseCase,
    RunHealthAlertFlowUseCase,
)
from VitalAI.domains.daily_life import DailyLifeCheckInSupportService
from VitalAI.domains.health import HealthAlertTriageService
from VitalAI.domains.reporting import FeedbackReportService
from VitalAI.platform.arbitration import GoalType
from VitalAI.platform.feedback import FeedbackEvent
from VitalAI.platform.runtime import DecisionCore, EventAggregator
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge
from VitalAI.platform.observability import ObservabilityCollector
from VitalAI.platform.security import SensitiveDataGuard


def build_runtime_signal_bridge() -> RuntimeSignalBridge:
    """Build a fresh bridge for application tests."""
    return RuntimeSignalBridge(
        observability=ObservabilityCollector(),
        security_guard=SensitiveDataGuard(),
    )


class TypedApplicationFlowTests(unittest.TestCase):
    def build_health_use_case(self) -> RunHealthAlertFlowUseCase:
        use_case = RunHealthAlertFlowUseCase(
            aggregator=EventAggregator(),
            decision_core=DecisionCore(),
            triage_service=HealthAlertTriageService(),
            signal_bridge=build_runtime_signal_bridge(),
        )
        use_case.configure_handlers()
        return use_case

    def build_daily_life_use_case(self) -> RunDailyLifeCheckInFlowUseCase:
        use_case = RunDailyLifeCheckInFlowUseCase(
            aggregator=EventAggregator(),
            decision_core=DecisionCore(),
            support_service=DailyLifeCheckInSupportService(),
            signal_bridge=build_runtime_signal_bridge(),
        )
        use_case.configure_handlers()
        return use_case

    def test_health_alert_flow_returns_typed_domain_outputs(self) -> None:
        use_case = self.build_health_use_case()
        command = HealthAlertCommand(
            source_agent="health-sensor-agent",
            trace_id="trace-health-1",
            user_id="elder-001",
            risk_level="critical",
        )

        result = use_case.run(command.to_message_envelope())

        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.summary)
        self.assertIsNotNone(result.outcome)
        self.assertEqual("HEALTH_ALERT", result.summary.event_type)
        self.assertEqual("HEALTH_DECISION", result.outcome.decision_message.msg_type)
        self.assertIsInstance(result.outcome.feedback_event, FeedbackEvent)
        self.assertEqual(GoalType.HEALTH, result.outcome.escalation_intent.goal_type)
        self.assertEqual("elder-001", result.outcome.decision_message.payload["user_id"])
        self.assertEqual(6, len(result.runtime_observations))
        self.assertEqual("EVENT_SUMMARY", result.runtime_observations[0].kind.value)
        self.assertEqual("SECURITY_REVIEW", result.runtime_observations[1].kind.value)
        self.assertEqual("RUNTIME_SNAPSHOT", result.runtime_observations[2].kind.value)
        self.assertEqual("SECURITY_REVIEW", result.runtime_observations[3].kind.value)
        self.assertEqual("INTERRUPT_SIGNAL", result.runtime_observations[4].kind.value)
        self.assertEqual("SECURITY_REVIEW", result.runtime_observations[5].kind.value)
        self.assertEqual(6, len(result.runtime_signals))
        self.assertEqual("EVENT_SUMMARY", result.runtime_signals[0].kind)
        self.assertEqual("HEALTH_ALERT", result.runtime_signals[0].details["event_type"])
        self.assertEqual("RUNTIME_SNAPSHOT", result.runtime_signals[2].kind)
        self.assertEqual("snapshot-", result.runtime_signals[2].details["snapshot_id"][:9])
        self.assertEqual("INTERRUPT_SIGNAL", result.runtime_signals[4].kind)
        self.assertEqual("TAKEOVER", result.runtime_signals[4].details["action"])
        self.assertEqual("decision-core", result.runtime_signals[4].details["target"])
        self.assertTrue(result.runtime_signals[4].details["has_snapshot_refs"])

    def test_health_alert_workflow_builds_feedback_report(self) -> None:
        workflow = HealthAlertWorkflow(
            use_case=self.build_health_use_case(),
            report_service=FeedbackReportService(),
        )
        command = HealthAlertCommand(
            source_agent="health-sensor-agent",
            trace_id="trace-health-2",
            user_id="elder-002",
            risk_level="high",
        )

        result = workflow.run(command)

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertIn("health-domain-service", result.feedback_report.title)
        self.assertIn("elder-002", result.feedback_report.body)
        self.assertEqual(2, len(result.flow_result.runtime_observations))
        self.assertEqual(2, len(result.flow_result.runtime_signals))
        self.assertEqual(2, len(result.runtime_signals))

    def test_health_alert_flow_executes_domain_service_once(self) -> None:
        triage_service = HealthAlertTriageService()
        triage_service.triage = Mock(wraps=triage_service.triage)
        use_case = RunHealthAlertFlowUseCase(
            aggregator=EventAggregator(),
            decision_core=DecisionCore(),
            triage_service=triage_service,
            signal_bridge=build_runtime_signal_bridge(),
        )
        use_case.configure_handlers()

        result = use_case.run(
            HealthAlertCommand(
                source_agent="health-sensor-agent",
                trace_id="trace-health-call-count-1",
                user_id="elder-003",
                risk_level="critical",
            ).to_message_envelope()
        )

        self.assertTrue(result.accepted)
        self.assertEqual(1, triage_service.triage.call_count)

    def test_daily_life_flow_returns_typed_domain_outputs(self) -> None:
        use_case = self.build_daily_life_use_case()
        command = DailyLifeCheckInCommand(
            source_agent="daily-life-sensor-agent",
            trace_id="trace-daily-1",
            user_id="elder-101",
            need="meal_support",
            urgency="high",
        )

        result = use_case.run(command.to_message_envelope())

        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.summary)
        self.assertIsNotNone(result.outcome)
        self.assertEqual("DAILY_LIFE_CHECKIN", result.summary.event_type)
        self.assertEqual("DAILY_LIFE_DECISION", result.outcome.decision_message.msg_type)
        self.assertEqual(GoalType.DAILY_LIFE, result.outcome.support_intent.goal_type)
        self.assertEqual("meal_support", result.outcome.decision_message.payload["need"])
        self.assertEqual(6, len(result.runtime_observations))
        self.assertEqual("EVENT_SUMMARY", result.runtime_observations[0].kind.value)
        self.assertEqual("RUNTIME_SNAPSHOT", result.runtime_observations[2].kind.value)
        self.assertEqual("INTERRUPT_SIGNAL", result.runtime_observations[4].kind.value)
        self.assertEqual(6, len(result.runtime_signals))
        self.assertEqual("RUNTIME_SNAPSHOT", result.runtime_signals[2].kind)
        self.assertTrue(result.runtime_signals[2].details["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", result.runtime_signals[4].kind)
        self.assertEqual("TAKEOVER", result.runtime_signals[4].details["action"])
        self.assertTrue(result.runtime_signals[4].details["has_snapshot_refs"])

    def test_daily_life_workflow_builds_feedback_report(self) -> None:
        workflow = DailyLifeCheckInWorkflow(
            use_case=self.build_daily_life_use_case(),
            report_service=FeedbackReportService(),
        )
        command = DailyLifeCheckInCommand(
            source_agent="daily-life-sensor-agent",
            trace_id="trace-daily-2",
            user_id="elder-102",
            need="mobility_support",
            urgency="normal",
        )

        result = workflow.run(command)

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertIn("daily-life-domain-service", result.feedback_report.title)
        self.assertIn("mobility_support", result.feedback_report.body)
        self.assertEqual(2, len(result.flow_result.runtime_observations))
        self.assertEqual(2, len(result.flow_result.runtime_signals))
        self.assertEqual(2, len(result.runtime_signals))

    def test_daily_life_flow_executes_domain_service_once(self) -> None:
        support_service = DailyLifeCheckInSupportService()
        support_service.support = Mock(wraps=support_service.support)
        use_case = RunDailyLifeCheckInFlowUseCase(
            aggregator=EventAggregator(),
            decision_core=DecisionCore(),
            support_service=support_service,
            signal_bridge=build_runtime_signal_bridge(),
        )
        use_case.configure_handlers()

        result = use_case.run(
            DailyLifeCheckInCommand(
                source_agent="daily-life-sensor-agent",
                trace_id="trace-daily-call-count-1",
                user_id="elder-103",
                need="meal_support",
                urgency="high",
            ).to_message_envelope()
        )

        self.assertTrue(result.accepted)
        self.assertEqual(1, support_service.support.call_count)


if __name__ == "__main__":
    unittest.main()
