"""Tests for typed application flow route adapters."""

from __future__ import annotations

import unittest
from pathlib import Path
import shutil
from uuid import uuid4
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from VitalAI.interfaces import typed_flow_support
from VitalAI.interfaces.api.app import init_http_interfaces
from VitalAI.interfaces.api.routers.typed_flows import (
    DailyLifeCheckInRequest,
    HealthAlertRequest,
    HealthAlertStatusUpdateRequest,
    MentalCareCheckInRequest,
    ProfileMemoryUpdateRequest,
    get_daily_life_checkin_detail,
    get_daily_life_checkin_history,
    get_health_alert_detail,
    get_health_alert_history,
    get_mental_care_checkin_detail,
    get_mental_care_checkin_history,
    get_profile_memory_snapshot,
    update_health_alert_status,
    get_health_failover_drill,
    get_intent_decomposer_status,
    get_runtime_diagnostics,
    get_runtime_policy,
    get_runtime_policy_matrix,
    get_runtime_policy_observation,
    run_daily_life_checkin,
    run_health_alert,
    run_mental_care_checkin,
    run_profile_memory_update,
    router,
)


class TypedFlowRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

    @staticmethod
    def build_test_client() -> TestClient:
        app = FastAPI(title="VitalAI Route Test App")
        init_http_interfaces(app)
        return TestClient(app)

    def test_health_alert_route_adapter_returns_expected_shape(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                response = run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-1",
                        user_id="elder-801",
                        risk_level="critical",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("HEALTH_ALERT", response["event_type"])
        self.assertEqual("HEALTH_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual("raised", response["health_alert_entry"]["status"])
        self.assertEqual("critical", response["health_alert_entry"]["risk_level"])
        self.assertEqual(1, response["health_alert_snapshot"]["alert_count"])
        self.assertEqual(["critical"], response["health_alert_snapshot"]["recent_risk_levels"])
        self.assertEqual(["raised"], response["health_alert_snapshot"]["recent_statuses"])
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

    def test_health_alert_history_route_adapter_returns_recent_alerts(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-read-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-read-high",
                        user_id="elder-810",
                        risk_level="high",
                    )
                )
                run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-read-critical",
                        user_id="elder-810",
                        risk_level="critical",
                    )
                )
                response = get_health_alert_history(
                    "elder-810",
                    source_agent="health-api",
                    trace_id="trace-api-health-read",
                    limit=1,
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-810", response["user_id"])
        self.assertEqual(1, response["health_alert_snapshot"]["alert_count"])
        self.assertEqual(["critical"], response["health_alert_snapshot"]["recent_risk_levels"])
        self.assertEqual(["raised"], response["health_alert_snapshot"]["recent_statuses"])
        self.assertEqual("raised", response["health_alert_snapshot"]["entries"][0]["status"])
        self.assertEqual("critical", response["health_alert_snapshot"]["entries"][0]["risk_level"])

    def test_health_alert_status_update_route_adapter_updates_single_alert(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-status-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                created = run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-status-create",
                        user_id="elder-8102",
                        risk_level="high",
                    )
                )
                acknowledge_response = update_health_alert_status(
                    "elder-8102",
                    created["health_alert_entry"]["alert_id"],
                    request=HealthAlertStatusUpdateRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-status-ack",
                    ),
                    target_status="acknowledged",
                )
                resolve_response = update_health_alert_status(
                    "elder-8102",
                    created["health_alert_entry"]["alert_id"],
                    request=HealthAlertStatusUpdateRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-status-resolve",
                    ),
                    target_status="resolved",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(acknowledge_response["accepted"])
        self.assertEqual("raised", acknowledge_response["previous_status"])
        self.assertEqual("acknowledged", acknowledge_response["current_status"])
        self.assertEqual(["acknowledged"], acknowledge_response["health_alert_snapshot"]["recent_statuses"])
        self.assertTrue(resolve_response["accepted"])
        self.assertEqual("acknowledged", resolve_response["previous_status"])
        self.assertEqual("resolved", resolve_response["current_status"])
        self.assertEqual(["resolved"], resolve_response["health_alert_snapshot"]["recent_statuses"])

    def test_health_alert_history_route_adapter_can_filter_by_status(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-filter-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                created = run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-filter-create",
                        user_id="elder-8103",
                        risk_level="high",
                    )
                )
                run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-filter-second",
                        user_id="elder-8103",
                        risk_level="critical",
                    )
                )
                update_health_alert_status(
                    "elder-8103",
                    created["health_alert_entry"]["alert_id"],
                    request=HealthAlertStatusUpdateRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-filter-ack",
                    ),
                    target_status="acknowledged",
                )
                response = get_health_alert_history(
                    "elder-8103",
                    source_agent="health-api",
                    trace_id="trace-api-health-filter-read",
                    status_filter="acknowledged",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual(1, response["health_alert_snapshot"]["alert_count"])
        self.assertEqual(["acknowledged"], response["health_alert_snapshot"]["recent_statuses"])
        self.assertEqual("acknowledged", response["health_alert_snapshot"]["entries"][0]["status"])

    def test_health_alert_detail_route_adapter_returns_single_alert(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-detail-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                created = run_health_alert(
                    HealthAlertRequest(
                        source_agent="health-api",
                        trace_id="trace-api-health-detail-create",
                        user_id="elder-8104",
                        risk_level="critical",
                    )
                )
                response = get_health_alert_detail(
                    "elder-8104",
                    created["health_alert_entry"]["alert_id"],
                    source_agent="health-api",
                    trace_id="trace-api-health-detail-read",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-8104", response["user_id"])
        self.assertEqual(created["health_alert_entry"]["alert_id"], response["alert_id"])
        self.assertEqual("critical", response["health_alert_entry"]["risk_level"])
        self.assertEqual("raised", response["health_alert_entry"]["status"])

    def test_health_alert_history_http_route_reads_after_alert(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-http-read-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-write",
                        "user_id": "elder-811",
                        "risk_level": "high",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/health-alerts/elder-811",
                    params={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-811", body["user_id"])
        self.assertEqual(1, body["health_alert_snapshot"]["alert_count"])
        self.assertEqual("high", body["health_alert_snapshot"]["entries"][0]["risk_level"])
        self.assertEqual("raised", body["health_alert_snapshot"]["entries"][0]["status"])

    def test_health_alert_history_http_route_can_filter_by_status(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-http-filter-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-filter-write",
                        "user_id": "elder-8113",
                        "risk_level": "high",
                    },
                )
                alert_id = write_response.json()["health_alert_entry"]["alert_id"]
                client.patch(
                    f"/vitalai/flows/health-alerts/elder-8113/{alert_id}/acknowledge",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-filter-ack",
                    },
                )
                client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-filter-second",
                        "user_id": "elder-8113",
                        "risk_level": "critical",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/health-alerts/elder-8113",
                    params={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-filter-read",
                        "status_filter": "acknowledged",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertEqual(1, body["health_alert_snapshot"]["alert_count"])
        self.assertEqual("acknowledged", body["health_alert_snapshot"]["entries"][0]["status"])

    def test_health_alert_detail_http_route_returns_single_alert(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-http-detail-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-detail-write",
                        "user_id": "elder-8114",
                        "risk_level": "critical",
                    },
                )
                alert_id = write_response.json()["health_alert_entry"]["alert_id"]
                detail_response = client.get(
                    f"/vitalai/flows/health-alerts/elder-8114/{alert_id}",
                    params={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-http-detail-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, detail_response.status_code)
        body = detail_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(alert_id, body["alert_id"])
        self.assertEqual("critical", body["health_alert_entry"]["risk_level"])

    def test_health_alert_detail_http_route_returns_not_found(self) -> None:
        client = self.build_test_client()

        response = client.get(
            "/vitalai/flows/health-alerts/elder-missing/404",
            params={
                "source_agent": "health-api",
                "trace_id": "trace-api-health-http-detail-missing",
            },
        )

        self.assertEqual(404, response.status_code)
        body = response.json()
        self.assertEqual("health_alert_not_found", body["detail"]["error"])
        self.assertEqual(404, body["detail"]["alert_id"])

    def test_health_alert_status_update_http_routes_enforce_valid_transitions(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"health-http-status-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "health.sqlite3")
            with patch.dict("os.environ", {"VITALAI_HEALTH_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/health-alert",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-status-http-write",
                        "user_id": "elder-8112",
                        "risk_level": "high",
                    },
                )
                alert_id = write_response.json()["health_alert_entry"]["alert_id"]
                acknowledge_response = client.patch(
                    f"/vitalai/flows/health-alerts/elder-8112/{alert_id}/acknowledge",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-status-http-ack",
                    },
                )
                resolve_response = client.patch(
                    f"/vitalai/flows/health-alerts/elder-8112/{alert_id}/resolve",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-status-http-resolve",
                    },
                )
                invalid_response = client.patch(
                    f"/vitalai/flows/health-alerts/elder-8112/{alert_id}/acknowledge",
                    json={
                        "source_agent": "health-api",
                        "trace_id": "trace-api-health-status-http-invalid",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, acknowledge_response.status_code)
        self.assertEqual(200, resolve_response.status_code)
        self.assertEqual(409, invalid_response.status_code)
        self.assertEqual("acknowledged", acknowledge_response.json()["current_status"])
        self.assertEqual("resolved", resolve_response.json()["current_status"])
        invalid_body = invalid_response.json()
        self.assertEqual("invalid_status_transition", invalid_body["detail"]["error"])
        self.assertEqual(alert_id, invalid_body["detail"]["alert_id"])

    def test_health_alert_status_update_http_route_returns_not_found(self) -> None:
        client = self.build_test_client()

        response = client.patch(
            "/vitalai/flows/health-alerts/elder-missing/404/resolve",
            json={
                "source_agent": "health-api",
                "trace_id": "trace-api-health-status-http-missing",
            },
        )

        self.assertEqual(404, response.status_code)
        body = response.json()
        self.assertEqual("health_alert_not_found", body["detail"]["error"])
        self.assertEqual(404, body["detail"]["alert_id"])

    def test_daily_life_route_adapter_returns_expected_shape(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                response = run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-1",
                        user_id="elder-802",
                        need="mobility_support",
                        urgency="high",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("DAILY_LIFE_CHECKIN", response["event_type"])
        self.assertEqual("DAILY_LIFE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual("mobility_support", response["checkin_entry"]["need"])
        self.assertEqual("high", response["checkin_entry"]["urgency"])
        self.assertEqual(1, response["daily_life_snapshot"]["checkin_count"])
        self.assertEqual(["mobility_support"], response["daily_life_snapshot"]["recent_needs"])
        self.assertEqual(6, len(response["runtime_signals"]))
        self.assertEqual("RUNTIME_SNAPSHOT", response["runtime_signals"][2]["kind"])
        self.assertTrue(response["runtime_signals"][2]["details"]["snapshot_id"].startswith("snapshot-"))
        self.assertEqual("INTERRUPT_SIGNAL", response["runtime_signals"][4]["kind"])
        self.assertTrue(response["runtime_signals"][4]["details"]["has_snapshot_refs"])

    def test_daily_life_history_route_adapter_returns_recent_checkins(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-read-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-read-meal",
                        user_id="elder-808",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-read-mobility",
                        user_id="elder-808",
                        need="mobility_support",
                        urgency="high",
                    )
                )
                response = get_daily_life_checkin_history(
                    "elder-808",
                    source_agent="daily-api",
                    trace_id="trace-api-daily-read",
                    limit=1,
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-808", response["user_id"])
        self.assertEqual(1, response["daily_life_snapshot"]["checkin_count"])
        self.assertEqual(["mobility_support"], response["daily_life_snapshot"]["recent_needs"])
        self.assertEqual("mobility_support", response["daily_life_snapshot"]["entries"][0]["need"])

    def test_daily_life_history_route_adapter_can_filter_by_urgency(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-filter-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-filter-normal",
                        user_id="elder-8082",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-filter-high",
                        user_id="elder-8082",
                        need="mobility_support",
                        urgency="high",
                    )
                )
                response = get_daily_life_checkin_history(
                    "elder-8082",
                    source_agent="daily-api",
                    trace_id="trace-api-daily-filter-read",
                    urgency_filter="high",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual(1, response["daily_life_snapshot"]["checkin_count"])
        self.assertEqual("high", response["daily_life_snapshot"]["entries"][0]["urgency"])
        self.assertEqual("mobility_support", response["daily_life_snapshot"]["entries"][0]["need"])

    def test_daily_life_detail_route_adapter_returns_single_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-detail-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                created = run_daily_life_checkin(
                    DailyLifeCheckInRequest(
                        source_agent="daily-api",
                        trace_id="trace-api-daily-detail-create",
                        user_id="elder-8083",
                        need="meal_support",
                        urgency="normal",
                    )
                )
                response = get_daily_life_checkin_detail(
                    "elder-8083",
                    created["checkin_entry"]["checkin_id"],
                    source_agent="daily-api",
                    trace_id="trace-api-daily-detail-read",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-8083", response["user_id"])
        self.assertEqual(created["checkin_entry"]["checkin_id"], response["checkin_id"])
        self.assertEqual("meal_support", response["daily_life_entry"]["need"])

    def test_daily_life_history_http_route_reads_after_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-http-read-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-write",
                        "user_id": "elder-809",
                        "need": "meal_support",
                        "urgency": "normal",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/daily-life-checkins/elder-809",
                    params={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-809", body["user_id"])
        self.assertEqual(1, body["daily_life_snapshot"]["checkin_count"])
        self.assertEqual("meal_support", body["daily_life_snapshot"]["entries"][0]["need"])

    def test_daily_life_history_http_route_can_filter_by_urgency(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-http-filter-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-filter-normal",
                        "user_id": "elder-8092",
                        "need": "meal_support",
                        "urgency": "normal",
                    },
                )
                client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-filter-high",
                        "user_id": "elder-8092",
                        "need": "mobility_support",
                        "urgency": "high",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/daily-life-checkins/elder-8092",
                    params={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-filter-read",
                        "urgency_filter": "high",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertEqual(1, body["daily_life_snapshot"]["checkin_count"])
        self.assertEqual("high", body["daily_life_snapshot"]["entries"][0]["urgency"])

    def test_daily_life_detail_http_route_returns_single_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"daily-life-http-detail-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "daily-life.sqlite3")
            with patch.dict("os.environ", {"VITALAI_DAILY_LIFE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/daily-life-checkin",
                    json={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-detail-write",
                        "user_id": "elder-8093",
                        "need": "meal_support",
                        "urgency": "normal",
                    },
                )
                checkin_id = write_response.json()["checkin_entry"]["checkin_id"]
                detail_response = client.get(
                    f"/vitalai/flows/daily-life-checkins/elder-8093/{checkin_id}",
                    params={
                        "source_agent": "daily-api",
                        "trace_id": "trace-api-daily-http-detail-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, detail_response.status_code)
        body = detail_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(checkin_id, body["checkin_id"])
        self.assertEqual("meal_support", body["daily_life_entry"]["need"])

    def test_daily_life_detail_http_route_returns_not_found(self) -> None:
        client = self.build_test_client()

        response = client.get(
            "/vitalai/flows/daily-life-checkins/elder-missing/404",
            params={
                "source_agent": "daily-api",
                "trace_id": "trace-api-daily-http-detail-missing",
            },
        )

        self.assertEqual(404, response.status_code)
        body = response.json()
        self.assertEqual("daily_life_checkin_not_found", body["detail"]["error"])
        self.assertEqual(404, body["detail"]["checkin_id"])

    def test_mental_care_route_adapter_returns_expected_shape(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                response = run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-1",
                        user_id="elder-803",
                        mood_signal="distressed",
                        support_need="emotional_checkin",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("MENTAL_CARE_CHECKIN", response["event_type"])
        self.assertEqual("MENTAL_CARE_DECISION", response["decision_type"])
        self.assertIsNotNone(response["feedback_report"])
        self.assertEqual("distressed", response["mental_care_entry"]["mood_signal"])
        self.assertEqual("emotional_checkin", response["mental_care_entry"]["support_need"])
        self.assertEqual(1, response["mental_care_snapshot"]["checkin_count"])
        self.assertEqual(["distressed"], response["mental_care_snapshot"]["recent_mood_signals"])
        self.assertEqual(2, len(response["runtime_signals"]))

    def test_mental_care_history_route_adapter_returns_recent_checkins(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-read-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-read-calm",
                        user_id="elder-812",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-read-distressed",
                        user_id="elder-812",
                        mood_signal="distressed",
                        support_need="emotional_checkin",
                    )
                )
                response = get_mental_care_checkin_history(
                    "elder-812",
                    source_agent="mental-api",
                    trace_id="trace-api-mental-read",
                    limit=1,
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-812", response["user_id"])
        self.assertEqual(1, response["mental_care_snapshot"]["checkin_count"])
        self.assertEqual(["distressed"], response["mental_care_snapshot"]["recent_mood_signals"])
        self.assertEqual("emotional_checkin", response["mental_care_snapshot"]["entries"][0]["support_need"])

    def test_mental_care_history_http_route_reads_after_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-http-read-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-write",
                        "user_id": "elder-813",
                        "mood_signal": "calm",
                        "support_need": "companionship",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/mental-care-checkins/elder-813",
                    params={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-813", body["user_id"])
        self.assertEqual(1, body["mental_care_snapshot"]["checkin_count"])
        self.assertEqual("calm", body["mental_care_snapshot"]["entries"][0]["mood_signal"])

    def test_mental_care_history_route_adapter_can_filter_by_mood(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-filter-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-filter-calm",
                        user_id="elder-8132",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-filter-distressed",
                        user_id="elder-8132",
                        mood_signal="distressed",
                        support_need="reassurance",
                    )
                )
                response = get_mental_care_checkin_history(
                    "elder-8132",
                    source_agent="mental-api",
                    trace_id="trace-api-mental-filter-read",
                    mood_filter="calm",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual(1, response["mental_care_snapshot"]["checkin_count"])
        self.assertEqual("calm", response["mental_care_snapshot"]["entries"][0]["mood_signal"])

    def test_mental_care_detail_route_adapter_returns_single_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-detail-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                created = run_mental_care_checkin(
                    MentalCareCheckInRequest(
                        source_agent="mental-api",
                        trace_id="trace-api-mental-detail-create",
                        user_id="elder-8133",
                        mood_signal="calm",
                        support_need="companionship",
                    )
                )
                response = get_mental_care_checkin_detail(
                    "elder-8133",
                    created["mental_care_entry"]["checkin_id"],
                    source_agent="mental-api",
                    trace_id="trace-api-mental-detail-read",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-8133", response["user_id"])
        self.assertEqual(created["mental_care_entry"]["checkin_id"], response["checkin_id"])
        self.assertEqual("calm", response["mental_care_entry"]["mood_signal"])

    def test_mental_care_history_http_route_can_filter_by_mood(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-http-filter-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-filter-calm",
                        "user_id": "elder-8134",
                        "mood_signal": "calm",
                        "support_need": "companionship",
                    },
                )
                client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-filter-distressed",
                        "user_id": "elder-8134",
                        "mood_signal": "distressed",
                        "support_need": "reassurance",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/mental-care-checkins/elder-8134",
                    params={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-filter-read",
                        "mood_filter": "calm",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertEqual(1, body["mental_care_snapshot"]["checkin_count"])
        self.assertEqual("calm", body["mental_care_snapshot"]["entries"][0]["mood_signal"])

    def test_mental_care_detail_http_route_returns_single_checkin(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"mental-care-http-detail-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "mental-care.sqlite3")
            with patch.dict("os.environ", {"VITALAI_MENTAL_CARE_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/mental-care-checkin",
                    json={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-detail-write",
                        "user_id": "elder-8135",
                        "mood_signal": "calm",
                        "support_need": "companionship",
                    },
                )
                checkin_id = write_response.json()["mental_care_entry"]["checkin_id"]
                detail_response = client.get(
                    f"/vitalai/flows/mental-care-checkins/elder-8135/{checkin_id}",
                    params={
                        "source_agent": "mental-api",
                        "trace_id": "trace-api-mental-http-detail-read",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, detail_response.status_code)
        body = detail_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual(checkin_id, body["checkin_id"])
        self.assertEqual("calm", body["mental_care_entry"]["mood_signal"])

    def test_mental_care_detail_http_route_returns_not_found(self) -> None:
        client = self.build_test_client()

        response = client.get(
            "/vitalai/flows/mental-care-checkins/elder-missing/404",
            params={
                "source_agent": "mental-api",
                "trace_id": "trace-api-mental-http-detail-missing",
            },
        )

        self.assertEqual(404, response.status_code)
        body = response.json()
        self.assertEqual("mental_care_checkin_not_found", body["detail"]["error"])
        self.assertEqual(404, body["detail"]["checkin_id"])

    def test_profile_memory_route_adapter_returns_persisted_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                response = run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-1",
                        user_id="elder-804",
                        memory_key="favorite_drink",
                        memory_value="ginger_tea",
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("PROFILE_MEMORY_UPDATE", response["event_type"])
        self.assertEqual("PROFILE_MEMORY_DECISION", response["decision_type"])
        self.assertEqual("favorite_drink", response["stored_entry"]["memory_key"])
        self.assertEqual("ginger_tea", response["stored_entry"]["memory_value"])
        self.assertEqual("elder-804", response["profile_snapshot"]["user_id"])
        self.assertEqual(1, response["profile_snapshot"]["memory_count"])
        self.assertEqual(["favorite_drink"], response["profile_snapshot"]["memory_keys"])
        self.assertEqual("1 profile memory entry: favorite_drink", response["profile_snapshot"]["readable_summary"])
        self.assertEqual("ginger_tea", response["profile_snapshot"]["entries"][0]["memory_value"])
        self.assertIsNotNone(response["feedback_report"])

    def test_profile_memory_snapshot_route_adapter_returns_current_snapshot(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-read-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-write",
                        user_id="elder-805",
                        memory_key="favorite_music",
                        memory_value="jazz",
                    )
                )
                response = get_profile_memory_snapshot(
                    "elder-805",
                    source_agent="profile-api",
                    trace_id="trace-api-profile-read",
                )
                empty_response = get_profile_memory_snapshot("elder-empty")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual("elder-805", response["user_id"])
        self.assertEqual("elder-805", response["profile_snapshot"]["user_id"])
        self.assertEqual(1, response["profile_snapshot"]["memory_count"])
        self.assertEqual(["favorite_music"], response["profile_snapshot"]["memory_keys"])
        self.assertEqual("1 profile memory entry: favorite_music", response["profile_snapshot"]["readable_summary"])
        self.assertEqual("favorite_music", response["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual("jazz", response["profile_snapshot"]["entries"][0]["memory_value"])
        self.assertTrue(empty_response["accepted"])
        self.assertEqual("elder-empty", empty_response["profile_snapshot"]["user_id"])
        self.assertEqual(0, empty_response["profile_snapshot"]["memory_count"])
        self.assertEqual([], empty_response["profile_snapshot"]["memory_keys"])
        self.assertEqual(
            "No profile memory entries for elder-empty.",
            empty_response["profile_snapshot"]["readable_summary"],
        )

    def test_profile_memory_snapshot_route_adapter_can_filter_by_key(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-read-key-route-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-key-write-drink",
                        user_id="elder-807",
                        memory_key="favorite_drink",
                        memory_value="ginger_tea",
                    )
                )
                run_profile_memory_update(
                    ProfileMemoryUpdateRequest(
                        source_agent="profile-api",
                        trace_id="trace-api-profile-key-write-music",
                        user_id="elder-807",
                        memory_key="favorite_music",
                        memory_value="jazz",
                    )
                )
                response = get_profile_memory_snapshot(
                    "elder-807",
                    source_agent="profile-api",
                    trace_id="trace-api-profile-key-read",
                    memory_key="favorite_drink",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertTrue(response["accepted"])
        self.assertEqual(1, response["profile_snapshot"]["memory_count"])
        self.assertEqual(["favorite_drink"], response["profile_snapshot"]["memory_keys"])
        self.assertEqual("1 profile memory entry: favorite_drink", response["profile_snapshot"]["readable_summary"])
        self.assertEqual("favorite_drink", response["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual("ginger_tea", response["profile_snapshot"]["entries"][0]["memory_value"])

    def test_profile_memory_snapshot_http_route_reads_after_update(self) -> None:
        runtime_dir = Path(".runtime")
        runtime_dir.mkdir(exist_ok=True)
        temp_dir = runtime_dir / f"profile-memory-http-read-{uuid4().hex}"
        temp_dir.mkdir()
        try:
            db_path = str(temp_dir / "profile-memory.sqlite3")
            with patch.dict("os.environ", {"VITALAI_PROFILE_MEMORY_DB_PATH": db_path}, clear=False):
                typed_flow_support._DEFAULT_ASSEMBLIES.clear()
                client = self.build_test_client()

                write_response = client.post(
                    "/vitalai/flows/profile-memory",
                    json={
                        "source_agent": "profile-api",
                        "trace_id": "trace-api-profile-http-write",
                        "user_id": "elder-806",
                        "memory_key": "walking_preference",
                        "memory_value": "morning",
                    },
                )
                read_response = client.get(
                    "/vitalai/flows/profile-memory/elder-806",
                    params={
                        "source_agent": "profile-api",
                        "trace_id": "trace-api-profile-http-read",
                        "memory_key": "walking_preference",
                    },
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(200, write_response.status_code)
        self.assertEqual(200, read_response.status_code)
        body = read_response.json()
        self.assertTrue(body["accepted"])
        self.assertEqual("elder-806", body["user_id"])
        self.assertEqual(1, body["profile_snapshot"]["memory_count"])
        self.assertEqual(["walking_preference"], body["profile_snapshot"]["memory_keys"])
        self.assertEqual("1 profile memory entry: walking_preference", body["profile_snapshot"]["readable_summary"])
        self.assertEqual("walking_preference", body["profile_snapshot"]["entries"][0]["memory_key"])
        self.assertEqual("morning", body["profile_snapshot"]["entries"][0]["memory_value"])

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

    def test_intent_decomposer_status_defaults_to_placeholder(self) -> None:
        typed_flow_support._DEFAULT_ASSEMBLIES.clear()

        response = get_intent_decomposer_status("api")

        self.assertEqual("api", response["runtime_role"])
        self.assertEqual("placeholder", response["mode"])
        self.assertEqual("placeholder", response["status"])
        self.assertFalse(response["llm_requested"])
        self.assertFalse(response["llm_configured"])
        self.assertEqual("non_executing_second_layer", response["execution_boundary"])

    def test_intent_decomposer_status_reflects_llm_configuration(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "VITALAI_INTENT_DECOMPOSER": "llm",
                "VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER": "openai_compatible",
                "VITALAI_INTENT_DECOMPOSER_LLM_MODEL": "glm-5.1",
                "VITALAI_INTENT_DECOMPOSER_LLM_API_KEY": "test-key",
                "VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/",
                "VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE": "0.0",
                "VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS": "5.0",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            response = get_intent_decomposer_status("api")

        self.assertEqual("llm", response["mode"])
        self.assertEqual("openai_compatible", response["provider"])
        self.assertEqual("llm_configured", response["status"])
        self.assertTrue(response["llm_requested"])
        self.assertTrue(response["llm_configured"])
        self.assertTrue(response["api_key_configured"])
        self.assertEqual("glm-5.1", response["model"])

    def test_runtime_control_routes_use_post_admin_paths(self) -> None:
        route_methods = {
            route.path: route.methods
            for route in router.routes
            if hasattr(route, "methods")
        }

        self.assertEqual({"POST"}, route_methods["/admin/runtime-diagnostics/{role}"])
        self.assertEqual({"POST"}, route_methods["/admin/runtime-diagnostics/{role}/health-failover"])
        self.assertEqual({"GET"}, route_methods["/flows/intent-decomposer-status/{role}"])
        self.assertNotIn("/flows/runtime-diagnostics/{role}", route_methods)
        self.assertNotIn("/flows/runtime-diagnostics/{role}/health-failover", route_methods)

    def test_runtime_control_routes_are_blocked_by_default_in_production(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            headers = {"X-VitalAI-Admin-Token": "test-admin-token"}
            diagnostics_response = client.post("/vitalai/admin/runtime-diagnostics/api", headers=headers)
            drill_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api/health-failover",
                headers=headers,
            )

        self.assertEqual(403, diagnostics_response.status_code)
        self.assertEqual(403, drill_response.status_code)

    def test_runtime_control_routes_require_configured_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            response = client.post("/vitalai/admin/runtime-diagnostics/api")

        self.assertEqual(403, response.status_code)
        self.assertIn("Admin control token is not configured", response.json()["detail"])

    def test_runtime_control_routes_reject_missing_or_invalid_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            missing_response = client.post("/vitalai/admin/runtime-diagnostics/api")
            invalid_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "wrong-token"},
            )

        self.assertEqual(403, missing_response.status_code)
        self.assertEqual(403, invalid_response.status_code)
        self.assertEqual("Invalid admin token.", missing_response.json()["detail"])
        self.assertEqual("Invalid admin token.", invalid_response.json()["detail"])

    def test_runtime_control_routes_can_be_enabled_explicitly_in_production(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("api", response.json()["runtime_role"])

    def test_runtime_control_routes_run_with_valid_admin_token(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "VITALAI_RUNTIME_CONTROL_ENABLED": "true",
                "VITALAI_ADMIN_TOKEN": "test-admin-token",
            },
            clear=False,
        ):
            typed_flow_support._DEFAULT_ASSEMBLIES.clear()
            client = self.build_test_client()

            diagnostics_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )
            drill_response = client.post(
                "/vitalai/admin/runtime-diagnostics/api/health-failover",
                headers={"X-VitalAI-Admin-Token": "test-admin-token"},
            )

        self.assertEqual(200, diagnostics_response.status_code)
        self.assertEqual("api", diagnostics_response.json()["runtime_role"])
        self.assertEqual(200, drill_response.status_code)
        self.assertEqual("api", drill_response.json()["runtime_role"])


if __name__ == "__main__":
    unittest.main()
