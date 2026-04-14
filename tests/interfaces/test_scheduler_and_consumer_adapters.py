"""Tests for scheduler and consumer thin adapters over typed flows."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from VitalAI.application.commands import HealthAlertCommand
from VitalAI.interfaces import typed_flow_support
from VitalAI.interfaces.consumers import (
    DailyLifeCheckInConsumedEvent,
    HealthAlertConsumedEvent,
    consume_daily_life_checkin,
    consume_health_alert,
)
from VitalAI.interfaces.scheduler import (
    ScheduledDailyLifeCheckInJob,
    ScheduledHealthAlertJob,
    run_scheduled_daily_life_checkin,
    run_scheduled_health_alert,
)


class SchedulerAndConsumerAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    def test_scheduled_health_alert_reuses_current_workflow_shape(self) -> None:
        response = run_scheduled_health_alert(
            ScheduledHealthAlertJob(
                source_agent="scheduler-health",
                trace_id="trace-scheduler-health-1",
                user_id="elder-1001",
                risk_level="critical",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("HEALTH_DECISION", response["decision_type"])
        self.assertIsNone(response["feedback_report"])
        self.assertEqual(0, len(response["runtime_signals"]))

    def test_scheduled_daily_life_reuses_current_workflow_shape(self) -> None:
        response = run_scheduled_daily_life_checkin(
            ScheduledDailyLifeCheckInJob(
                source_agent="scheduler-daily",
                trace_id="trace-scheduler-daily-1",
                user_id="elder-1002",
                need="meal_support",
                urgency="high",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("DAILY_LIFE_DECISION", response["decision_type"])
        self.assertIsNone(response["feedback_report"])
        self.assertEqual(0, len(response["runtime_signals"]))

    def test_consumer_health_alert_reuses_current_workflow_shape(self) -> None:
        response = consume_health_alert(
            HealthAlertConsumedEvent(
                source_agent="consumer-health",
                trace_id="trace-consumer-health-1",
                user_id="elder-1003",
                risk_level="high",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("HEALTH_ALERT", response["event_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(2, len(response["runtime_signals"]))

    def test_consumer_daily_life_reuses_current_workflow_shape(self) -> None:
        response = consume_daily_life_checkin(
            DailyLifeCheckInConsumedEvent(
                source_agent="consumer-daily",
                trace_id="trace-consumer-daily-1",
                user_id="elder-1004",
                need="mobility_support",
                urgency="normal",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("DAILY_LIFE_CHECKIN", response["event_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(2, len(response["runtime_signals"]))

    def test_consumer_assembly_enforces_ack_policy(self) -> None:
        assembly = typed_flow_support.get_consumer_application_assembly()
        envelope = HealthAlertCommand(
            source_agent="consumer-health",
            trace_id="trace-consumer-health-ack-1",
            user_id="elder-1006",
            risk_level="high",
        ).to_message_envelope()
        envelope.require_ack = False

        adjusted = assembly.apply_ingress_policy(envelope)

        self.assertTrue(adjusted.require_ack)
        self.assertEqual(60, adjusted.ttl)

    def test_scheduler_assembly_can_reflect_explicit_reporting_override(self) -> None:
        with patch.dict("os.environ", {"VITALAI_REPORTING_ENABLED": "true"}):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            response = run_scheduled_health_alert(
                ScheduledHealthAlertJob(
                    source_agent="scheduler-health",
                    trace_id="trace-scheduler-health-2",
                    user_id="elder-1005",
                    risk_level="critical",
                )
            )

        self.assertTrue(response["accepted"])
        self.assertIsNotNone(response["feedback_report"])

    def test_scheduler_assembly_can_reflect_explicit_runtime_signal_override(self) -> None:
        with patch.dict("os.environ", {"VITALAI_RUNTIME_SIGNALS_ENABLED": "true"}):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            response = run_scheduled_health_alert(
                ScheduledHealthAlertJob(
                    source_agent="scheduler-health",
                    trace_id="trace-scheduler-health-3",
                    user_id="elder-1010",
                    risk_level="critical",
                )
            )

        self.assertTrue(response["accepted"])
        self.assertEqual(6, len(response["runtime_signals"]))

    def test_role_specific_interface_assemblies_are_cached_separately(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

        api_assembly = typed_flow_support.get_api_application_assembly()
        scheduler_assembly = typed_flow_support.get_scheduler_application_assembly()
        consumer_assembly = typed_flow_support.get_consumer_application_assembly()

        self.assertEqual("api", api_assembly.runtime_role)
        self.assertEqual("scheduler", scheduler_assembly.runtime_role)
        self.assertEqual("consumer", consumer_assembly.runtime_role)
        self.assertIsNot(api_assembly, scheduler_assembly)
        self.assertIsNot(scheduler_assembly, consumer_assembly)

        scheduler_envelope = HealthAlertCommand(
            source_agent="scheduler-health",
            trace_id="trace-scheduler-health-ttl-1",
            user_id="elder-1007",
            risk_level="high",
        ).to_message_envelope()
        api_envelope = HealthAlertCommand(
            source_agent="api-health",
            trace_id="trace-api-health-ttl-2",
            user_id="elder-1008",
            risk_level="high",
        ).to_message_envelope()

        self.assertEqual(300, scheduler_assembly.apply_ingress_policy(scheduler_envelope).ttl)
        self.assertEqual(30, api_assembly.apply_ingress_policy(api_envelope).ttl)

    def test_interface_support_can_expose_policy_snapshot(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

        snapshot = typed_flow_support.get_application_policy_snapshot("consumer")

        self.assertEqual("consumer", snapshot.runtime_role)
        self.assertTrue(snapshot.reporting_enabled)
        self.assertEqual("assembly_default", snapshot.reporting_policy_source)
        self.assertTrue(snapshot.runtime_signals_enabled)
        self.assertEqual("assembly_default", snapshot.runtime_signals_policy_source)
        self.assertTrue(snapshot.require_ack_override)
        self.assertEqual(60, snapshot.ttl_override)
        self.assertEqual("role_default", snapshot.ingress_policy_source)

    def test_interface_support_can_expose_runtime_diagnostics(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

        diagnostics = typed_flow_support.get_application_runtime_diagnostics("scheduler")

        self.assertEqual("scheduler", diagnostics.runtime_role)
        self.assertEqual("scheduler-runtime-snapshot", diagnostics.snapshot_id)
        self.assertTrue(diagnostics.failover_triggered)
        self.assertEqual("shadow", diagnostics.active_node)
        self.assertEqual([], diagnostics.runtime_signals)

    def test_interface_support_can_expose_health_failover_drill(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

        diagnostics = typed_flow_support.get_application_health_failover_drill("scheduler")

        self.assertEqual("scheduler", diagnostics.runtime_role)
        self.assertIsNone(diagnostics.snapshot_id)
        self.assertFalse(diagnostics.failover_triggered)
        self.assertEqual("primary", diagnostics.active_node)
        self.assertEqual([], diagnostics.runtime_signals)


if __name__ == "__main__":
    unittest.main()
