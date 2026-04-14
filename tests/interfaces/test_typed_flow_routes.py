"""Tests for typed application flow route adapters."""

from __future__ import annotations

import unittest

from VitalAI.interfaces import typed_flow_support
from VitalAI.interfaces.api.routers.typed_flows import (
    DailyLifeCheckInRequest,
    HealthAlertRequest,
    MentalCareCheckInRequest,
    get_health_failover_drill,
    get_runtime_diagnostics,
    get_runtime_policy,
    get_runtime_policy_matrix,
    get_runtime_policy_observation,
    run_daily_life_checkin,
    run_health_alert,
    run_mental_care_checkin,
)


class TypedFlowRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    def test_health_alert_route_adapter_returns_expected_shape(self) -> None:
        response = run_health_alert(
            HealthAlertRequest(
                source_agent="health-api",
                trace_id="trace-api-health-1",
                user_id="elder-801",
                risk_level="critical",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("HEALTH_ALERT", response["event_type"])
        self.assertEqual("HEALTH_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(6, len(response["runtime_signals"]))
        self.assertEqual("EVENT_SUMMARY", response["runtime_signals"][0]["kind"])
        self.assertEqual("HEALTH_ALERT", response["runtime_signals"][0]["details"]["event_type"])
        self.assertEqual("SECURITY_REVIEW", response["runtime_signals"][1]["kind"])
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertEqual("TAKEOVER", response["runtime_signals"][4]["details"]["action"])
        self.assertEqual("decision-core", response["runtime_signals"][4]["details"]["target"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])

    def test_daily_life_route_adapter_returns_expected_shape(self) -> None:
        response = run_daily_life_checkin(
            DailyLifeCheckInRequest(
                source_agent="daily-api",
                trace_id="trace-api-daily-1",
                user_id="elder-802",
                need="mobility_support",
                urgency="high",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("DAILY_LIFE_CHECKIN", response["event_type"])
        self.assertEqual("DAILY_LIFE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(6, len(response["runtime_signals"]))
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])

    def test_mental_care_route_adapter_returns_expected_shape(self) -> None:
        response = run_mental_care_checkin(
            MentalCareCheckInRequest(
                source_agent="mental-api",
                trace_id="trace-api-mental-1",
                user_id="elder-803",
                mood_signal="distressed",
                support_need="emotional_checkin",
            )
        )

        self.assertTrue(response["accepted"])
        self.assertEqual("MENTAL_CARE_CHECKIN", response["event_type"])
        self.assertEqual("MENTAL_CARE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual(2, len(response["runtime_signals"]))

    def test_runtime_policy_route_exposes_scheduler_policy_snapshot(self) -> None:
        response = get_runtime_policy("scheduler")

        self.assertEqual("scheduler", response["runtime_role"])
        self.assertFalse(response["reporting_enabled"])
        self.assertEqual("role_default", response["reporting_policy_source"])
        self.assertFalse(response["require_ack_override"])
        self.assertEqual(300, response["ttl_override"])
        self.assertEqual("role_default", response["ingress_policy_source"])

    def test_runtime_policy_matrix_route_exposes_all_standard_roles(self) -> None:
        response = get_runtime_policy_matrix()

        self.assertEqual({"default", "api", "scheduler", "consumer"}, set(response))
        self.assertTrue(response["api"]["reporting_enabled"])
        self.assertEqual("assembly_default", response["api"]["reporting_policy_source"])
        self.assertFalse(response["scheduler"]["reporting_enabled"])
        self.assertEqual("role_default", response["scheduler"]["reporting_policy_source"])
        self.assertFalse(response["scheduler"]["runtime_signals_enabled"])
        self.assertEqual("role_default", response["scheduler"]["runtime_signals_policy_source"])
        self.assertTrue(response["consumer"]["require_ack_override"])
        self.assertEqual(60, response["consumer"]["ttl_override"])
        self.assertEqual("role_default", response["consumer"]["ingress_policy_source"])

    def test_runtime_policy_observation_route_exposes_observability_shape(self) -> None:
        response = get_runtime_policy_observation("scheduler")

        self.assertEqual("POLICY_SNAPSHOT", response["kind"])
        self.assertEqual("INFO", response["severity"])
        self.assertEqual("application-assembly", response["source"])
        self.assertEqual("scheduler", response["attributes"]["runtime_role"])
        self.assertFalse(response["attributes"]["reporting_enabled"])
        self.assertEqual("role_default", response["attributes"]["reporting_policy_source"])
        self.assertFalse(response["attributes"]["runtime_signals_enabled"])
        self.assertEqual("role_default", response["attributes"]["runtime_signals_policy_source"])
        self.assertEqual("role_default", response["attributes"]["ingress_policy_source"])

    def test_runtime_diagnostics_route_exposes_snapshot_and_failover_signals(self) -> None:
        response = get_runtime_diagnostics("api")

        self.assertEqual("api", response["runtime_role"])
        self.assertEqual("api-runtime-snapshot", response["snapshot_id"])
        self.assertTrue(response["failover_triggered"])
        self.assertEqual("shadow", response["active_node"])
        self.assertIsNone(response["interrupt_action"])
        self.assertIsNone(response["interrupt_has_snapshot_refs"])
        self.assertEqual("ALLOW", response["latest_security_action"])
        self.assertEqual(0, response["latest_security_finding_count"])
        self.assertEqual("INFO", response["latest_security_highest_severity"])
        self.assertIsNotNone(response["latest_failover_signal_id"])
        self.assertEqual(3, len(response["runtime_signals"]))
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][0]["kind"])
        self.assertEqual("FAILOVER_TRANSITION", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["has_snapshot_refs"])
        self.assertEqual(["api-runtime-snapshot"], response["runtime_signals"][2]["details"]["snapshot_ids"])

    def test_health_failover_drill_route_exposes_controlled_failover_path(self) -> None:
        response = get_health_failover_drill("api")

        self.assertEqual("api", response["runtime_role"])
        self.assertTrue(response["failover_triggered"])
        self.assertEqual("shadow", response["active_node"])
        self.assertTrue(response["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("TAKEOVER", response["interrupt_action"])
        self.assertTrue(response["interrupt_has_snapshot_refs"])
        self.assertEqual("ALLOW", response["latest_security_action"])
        self.assertEqual(0, response["latest_security_finding_count"])
        self.assertEqual("INFO", response["latest_security_highest_severity"])
        self.assertIsNotNone(response["latest_failover_signal_id"])
        self.assertEqual(7, len(response["runtime_signals"]))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])
        self.assertEqual("FAILOVER_TRANSITION", response["runtime_signals"][6]["kind"])
        self.assertTrue(response["runtime_signals"][6]["details"]["has_snapshot_refs"])
        self.assertEqual([response["snapshot_id"]], response["runtime_signals"][6]["details"]["snapshot_ids"])


if __name__ == "__main__":
    unittest.main()
