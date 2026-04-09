# -*- coding: utf-8 -*-
"""Tests for student care data endpoints."""

from services.student_care_graph_service import student_care_graph_service
from tests.conftest import auth_headers, create_client, login_as


def test_admin_can_list_attendance_without_student_id():
    client = create_client()
    token = login_as(client, username="admin", password="admin123")
    headers = auth_headers(token)

    response = client.get("/api/attendance", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "list" in body["data"]


def test_teacher_list_requires_student_id():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    response = client.get("/api/attendance", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 403


def test_teacher_can_list_attendance_for_own_student():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    response = client.get("/api/attendance?student_id=1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "list" in body["data"]


def test_admin_can_create_and_delete_attendance():
    client = create_client()
    token = login_as(client, username="admin", password="admin123")
    headers = auth_headers(token)

    payload = {
        "student_id": 1,
        "date": "2026-04-07",
        "status": "late",
        "remark": "测试迟到"
    }
    create_resp = client.post("/api/attendance", json=payload, headers=headers)
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    delete_resp = client.delete(f"/api/attendance/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    delete_body = delete_resp.json()
    assert delete_body["code"] == 200


def test_attendance_change_triggers_graph_sync(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)
    captured = {"ids": []}

    monkeypatch.setattr(
        student_care_graph_service,
        "sync_student_graph",
        lambda db, student_id: captured["ids"].append(student_id) or {"enabled": True, "synced": True},
    )

    create_resp = client.post(
        "/api/attendance",
        json={
            "student_id": 1,
            "date": "2026-04-07",
            "status": "late",
            "remark": "图谱联动测试",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    record_id = create_resp.json()["data"]["id"]
    assert captured["ids"][-1] == 1

    delete_resp = client.delete(f"/api/attendance/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert captured["ids"][-1] == 1


def test_attendance_remark_is_included_in_student_care_signal():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    remark = "因家庭临时安排迟到，需要班主任后续关怀"
    create_resp = client.post(
        "/api/attendance",
        json={
            "student_id": 1,
            "date": "2026-04-07",
            "status": "late",
            "remark": remark,
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    try:
        profile_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()
        assert profile_body["code"] == 200
        attendance_signals = [
            item
            for item in profile_body["data"]["signals"]
            if item["source"] == "attendance" and item["signal_type"] == "attendance_late"
        ]
        assert any(remark in item["signal_text"] for item in attendance_signals)
    finally:
        client.delete(f"/api/attendance/{record_id}", headers=headers)


def test_admin_can_create_and_delete_behavior_event():
    client = create_client()
    token = login_as(client, username="admin", password="admin123")
    headers = auth_headers(token)

    payload = {
        "student_id": 1,
        "event_type": "discipline",
        "event_level": "medium",
        "event_desc": "测试行为事件",
        "occurred_at": "2026-04-07 09:30:00"
    }
    create_resp = client.post("/api/behavior-events", json=payload, headers=headers)
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    delete_resp = client.delete(f"/api/behavior-events/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    delete_body = delete_resp.json()
    assert delete_body["code"] == 200


def test_behavior_change_triggers_graph_sync(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)
    captured = {"ids": []}

    monkeypatch.setattr(
        student_care_graph_service,
        "sync_student_graph",
        lambda db, student_id: captured["ids"].append(student_id) or {"enabled": True, "synced": True},
    )

    create_resp = client.post(
        "/api/behavior-events",
        json={
            "student_id": 1,
            "event_type": "bullying",
            "event_level": "medium",
            "event_desc": "图谱联动删除测试",
            "occurred_at": "2026-04-07 10:20:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    record_id = create_resp.json()["data"]["id"]
    assert captured["ids"][-1] == 1

    delete_resp = client.delete(f"/api/behavior-events/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert captured["ids"][-1] == 1


def test_safety_behavior_event_is_included_in_student_care_signal():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    desc = "课间出现疑似欺凌线索，需要核实同伴关系"
    create_resp = client.post(
        "/api/behavior-events",
        json={
            "student_id": 1,
            "event_type": "bullying",
            "event_level": "medium",
            "event_desc": desc,
            "occurred_at": "2026-04-07 10:20:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    try:
        profile_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()
        assert profile_body["code"] == 200
        safety_signals = [
            item
            for item in profile_body["data"]["signals"]
            if item["source"] == "behavior_event" and item["dimension"] == "safety"
        ]
        assert any(desc in item["signal_text"] for item in safety_signals)
    finally:
        client.delete(f"/api/behavior-events/{record_id}", headers=headers)


def test_care_observation_is_included_in_student_care_signal():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    summary = "关怀谈话中学生提到近期情绪低落，需要继续观察"
    create_resp = client.post(
        "/api/care-observations",
        json={
            "student_id": 1,
            "dimension": "emotion",
            "observation_type": "care_talk",
            "observation_level": "medium",
            "observed_at": "2026-04-07 15:30:00",
            "summary": summary,
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    try:
        list_resp = client.get("/api/care-observations?student_id=1", headers=headers)
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        assert list_body["code"] == 200
        assert any(item["summary"] == summary for item in list_body["data"]["list"])

        profile_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()
        assert profile_body["code"] == 200
        observation_signals = [
            item
            for item in profile_body["data"]["signals"]
            if item["source"] == "care_observation" and item["dimension"] == "emotion"
        ]
        assert any(summary in item["signal_text"] for item in observation_signals)
    finally:
        client.delete(f"/api/care-observations/{record_id}", headers=headers)


def test_positive_care_observation_becomes_protective_signal():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    summary = "近期愿意主动参与班级活动，与同学互动明显好转，情绪状态稳定"
    create_resp = client.post(
        "/api/care-observations",
        json={
            "student_id": 1,
            "dimension": "social",
            "observation_type": "social_observation",
            "observation_level": "medium",
            "observed_at": "2026-04-09 15:30:00",
            "summary": summary,
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    record_id = create_resp.json()["data"]["id"]

    try:
        profile_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()
        social_signals = [
            item
            for item in profile_body["data"]["signals"]
            if item["source"] == "care_observation" and item["dimension"] == "social"
        ]
        assert any(item["signal_type"].startswith("care_observation_positive_") for item in social_signals)
        assert any(item["signal_weight"] < 0 for item in social_signals)
    finally:
        client.delete(f"/api/care-observations/{record_id}", headers=headers)


def test_admin_can_create_and_delete_family_contact():
    client = create_client()
    token = login_as(client, username="admin", password="admin123")
    headers = auth_headers(token)

    payload = {
        "student_id": 1,
        "contact_type": "phone",
        "summary": "测试家校沟通"
    }
    create_resp = client.post("/api/family-contacts", json=payload, headers=headers)
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    delete_resp = client.delete(f"/api/family-contacts/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    delete_body = delete_resp.json()
    assert delete_body["code"] == 200


def test_positive_family_contact_becomes_protective_signal():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    create_resp = client.post(
        "/api/family-contacts",
        json={
            "student_id": 1,
            "contact_type": "phone",
            "summary": "家长持续支持，愿意积极配合学校安排，学生状态逐步稳定",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    record_id = create_resp.json()["data"]["id"]

    try:
        profile_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()
        family_signals = [
            item
            for item in profile_body["data"]["signals"]
            if item["source"] == "family_contact"
        ]
        assert any(item["signal_type"] == "family_contact_positive" for item in family_signals)
        assert any(item["signal_weight"] < 0 for item in family_signals)
    finally:
        client.delete(f"/api/family-contacts/{record_id}", headers=headers)


def test_missing_score_does_not_raise_study_risk_and_is_reported_as_data_gap():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    create_resp = client.post(
        "/api/students",
        json={
            "student_no": "TEMP-RULE-001",
            "name": "规则测试生",
            "gender": "male",
            "age": 16,
            "grade": "高一",
            "class_id": 1,
            "contact": "",
            "specialty": "",
            "tags": "",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    student_id = create_resp.json()["data"]["id"]

    try:
        profile_resp = client.get(f"/api/student-care/profile/{student_id}", headers=headers)
        assert profile_resp.status_code == 200
        profile_body = profile_resp.json()["data"]
        assert profile_body["profile"]["study_score"] == 0.0
        assert "score_missing" in profile_body["data_quality"]["missing_sources"]
        gap_signals = [
            item for item in profile_body["signals"] if item["signal_type"] == "score_missing"
        ]
        assert gap_signals
        assert gap_signals[0]["signal_weight"] == 0.0
    finally:
        client.delete(f"/api/students/{student_id}", headers=auth_headers(login_as(client)))


def test_admin_can_create_and_list_assistant_summary():
    client = create_client()
    token = login_as(client, username="admin", password="admin123")
    headers = auth_headers(token)

    payload = {
        "student_id": 1,
        "summary_text": "测试助手摘要",
        "signals_json": {
            "signals": [
                {"dimension": "social", "weight": 0.35, "text": "测试社交信号", "type": "assistant_signal"}
            ]
        }
    }
    create_resp = client.post("/api/assistant-summary", json=payload, headers=headers)
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    assert create_body["data"]["id"] is not None

    list_resp = client.get("/api/assistant-summary?student_id=1", headers=headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["code"] == 200
    assert "list" in list_body["data"]


def test_teacher_can_create_and_delete_same_class_graph_relation():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    create_resp = client.post(
        "/api/graph-relations",
        json={
            "student_id": 1,
            "target_type": "student",
            "target_student_id": 2,
            "relation_type": "peer_support",
            "dimension": "social",
            "relation_level": "medium",
            "summary": "same class peer support",
            "occurred_at": "2026-04-09 10:20:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["code"] == 200
    record_id = create_body["data"]["id"]

    list_resp = client.get("/api/graph-relations?student_id=1", headers=headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["code"] == 200
    assert any(item["id"] == record_id for item in list_body["data"]["list"])

    delete_resp = client.delete(f"/api/graph-relations/{record_id}", headers=headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["code"] == 200


def test_teacher_cannot_create_cross_class_graph_relation():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    response = client.post(
        "/api/graph-relations",
        json={
            "student_id": 1,
            "target_type": "student",
            "target_student_id": 10,
            "relation_type": "concern",
            "dimension": "social",
            "relation_level": "low",
            "summary": "cross class relation should be blocked",
            "occurred_at": "2026-04-09 10:30:00",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 403


def test_protective_graph_relation_reduces_social_risk():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    baseline_resp = client.get("/api/student-care/profile/1", headers=headers)
    assert baseline_resp.status_code == 200
    baseline = baseline_resp.json()["data"]["profile"]

    create_resp = client.post(
        "/api/graph-relations",
        json={
            "student_id": 1,
            "target_type": "student",
            "target_student_id": 2,
            "relation_type": "peer_support",
            "dimension": "social",
            "relation_level": "medium",
            "summary": "protective peer support",
            "occurred_at": "2026-04-09 10:40:00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    record_id = create_resp.json()["data"]["id"]

    try:
        after_resp = client.get("/api/student-care/profile/1", headers=headers)
        assert after_resp.status_code == 200
        profile = after_resp.json()["data"]["profile"]
        assert profile["social_score"] < baseline["social_score"]
    finally:
        client.delete(f"/api/graph-relations/{record_id}", headers=headers)


def test_social_bayes_final_score_is_applied_to_social_score(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(student_care_graph_service, "enabled", True)
    monkeypatch.setattr(
        student_care_graph_service,
        "build_graph_signals",
        lambda db, student: [
            {
                "signal_type": "graph_social_isolation",
                "dimension": "social",
                "signal_text": "missing stable peer links",
                "signal_weight": 0.18,
                "source": "graph",
            }
        ],
    )

    response = client.get("/api/student-care/profile/1", headers=headers)
    assert response.status_code == 200
    profile = response.json()["data"]["profile"]
    assert profile["social_score"] == profile["social_final_score"]
    assert profile["social_bayes_posterior"] > 0
