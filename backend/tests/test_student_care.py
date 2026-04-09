# -*- coding: utf-8 -*-
"""Tests for student care profile."""

from api import student_care as student_care_api
from services import student_care_isolation_service
from services.student_care_graph_service import student_care_graph_service
from tests.conftest import auth_headers, create_client, login_as


def test_head_teacher_can_view_student_care_profile():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    response = client.get("/api/student-care/profile/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["student"]["name"] == "李明"
    assert "profile" in body["data"]
    assert "signals" in body["data"]


def test_non_head_teacher_cannot_view_student_care_profile():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    response = client.get("/api/student-care/profile/10", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 403


def test_teacher_can_confirm_student_care_agent_review(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)
    captured = {}

    def fake_confirm(db, current_user, record_id, payload):
        captured["username"] = current_user.username
        captured["record_id"] = record_id
        captured["resolution_status"] = payload.resolution_status
        captured["teacher_notes"] = payload.teacher_notes
        captured["summary"] = payload.reviewed_result["dimensions"][0]["summary"]
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": record_id,
                "review_status": "confirmed",
                "resolution_status": payload.resolution_status,
            },
        }

    monkeypatch.setattr(student_care_api.student_care_agent_service, "confirm_agent_eval_review", fake_confirm)

    response = client.post(
        "/api/student-care/agent-eval-review/25",
        json={
            "reviewed_result": {
                "suggestions": ["继续观察"],
                "dimensions": [
                    {
                        "dimension": "emotion",
                        "summary": "老师已完成初步安抚",
                        "evidence": ["已谈话"],
                    }
                ],
            },
            "teacher_notes": "已和家长沟通",
            "resolution_status": "in_progress",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["review_status"] == "confirmed"
    assert captured["username"] == "wang_math"
    assert captured["record_id"] == 25
    assert captured["resolution_status"] == "in_progress"
    assert captured["teacher_notes"] == "已和家长沟通"
    assert captured["summary"] == "老师已完成初步安抚"


def test_profile_supports_independent_isolation_bn_plugin(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_isolation_service,
        "build_student_isolation_analysis_payload",
        lambda db, student: {
            "student_id": student.id,
            "scene": "social_isolation",
            "risk_probability": 0.68,
            "risk_level": "medium",
            "confidence": 0.81,
            "root_causes": [
                {
                    "node": "peer_disconnect",
                    "label": "同伴连接缺失",
                    "probability": 0.73,
                    "impact": 0.92,
                    "contribution": 0.67,
                    "description": "缺少稳定同伴连接",
                    "evidence": [],
                }
            ],
            "propagation_paths": [
                {
                    "path_id": "peer_disconnect",
                    "nodes": ["同伴连接缺失", "社交退缩", "孤立风险"],
                    "path_probability": 0.51,
                    "summary": "同伴连接不足推动社交退缩。",
                }
            ],
            "evidence_summary": {
                "matched_signal_count": 2,
                "protective_factor_count": 0,
                "key_evidence": [],
                "protective_factors": [],
            },
            "network_snapshot": {
                "social_withdrawal_probability": 0.62,
                "source_count": 3,
                "inference_version": "isolation_bn_v1",
            },
        },
    )

    response = client.get("/api/student-care/isolation-bn/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["scene"] == "social_isolation"
    assert body["data"]["risk_probability"] == 0.68
    assert body["data"]["root_causes"][0]["node"] == "peer_disconnect"


def test_teacher_review_payload_supports_structured_labels(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)
    captured = {}

    def fake_confirm(db, current_user, record_id, payload):
        captured["record_id"] = record_id
        captured["scene"] = payload.review_labels.scene
        captured["is_true_risk"] = payload.review_labels.is_true_risk
        captured["severity"] = payload.review_labels.severity
        captured["confidence_by_teacher"] = payload.review_labels.confidence_by_teacher
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": record_id,
                "review_status": "confirmed",
                "review_labels": payload.review_labels.model_dump(),
            },
        }

    monkeypatch.setattr(student_care_api.student_care_agent_service, "confirm_agent_eval_review", fake_confirm)

    response = client.post(
        "/api/student-care/agent-eval-review/26",
        json={
            "reviewed_result": {"suggestions": [], "dimensions": []},
            "teacher_notes": "已安排持续关注",
            "resolution_status": "in_progress",
            "review_labels": {
                "scene": "social_isolation",
                "is_true_risk": "yes",
                "severity": "medium",
                "confidence_by_teacher": 4,
                "intervention_taken": "已安排同伴支持",
                "follow_up_outcome": "待一周后回访",
            },
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert captured["record_id"] == 26
    assert captured["scene"] == "social_isolation"
    assert captured["is_true_risk"] == "yes"
    assert captured["severity"] == "medium"
    assert captured["confidence_by_teacher"] == 4


def test_teacher_can_view_student_care_evaluation_summary(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_api.student_care_agent_service,
        "get_agent_evaluation_summary",
        lambda **kwargs: {
            "code": 200,
            "msg": "success",
            "data": {
                "total_records": 12,
                "confirmed_reviews": 8,
                "reviewed_ratio": 0.6667,
                "true_risk_count": 5,
                "false_alarm_count": 2,
                "unresolved_count": 3,
                "agreement_rate": 0.75,
                "avg_teacher_confidence": 4.1,
                "scene_distribution": {"social_isolation": 4},
                "severity_distribution": {"low": 1, "medium": 3, "high": 1, "unknown": 0},
                "resolution_distribution": {"pending": 1, "in_progress": 2, "resolved": 3, "false_alarm": 2},
                "system_vs_teacher": {
                    "aligned": 6,
                    "misaligned": 2,
                    "system_positive_teacher_yes": 4,
                    "system_positive_teacher_no": 1,
                    "system_low_teacher_yes": 1,
                    "system_low_teacher_no": 2,
                },
                "trend": [{"date": "2026-04-09", "confirmed_count": 2, "true_risk_count": 1}],
            },
        },
    )

    response = client.get("/api/student-care/evaluation-summary", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["confirmed_reviews"] == 8
    assert body["data"]["scene_distribution"]["social_isolation"] == 4


def test_teacher_can_export_student_care_evaluation_summary(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_api.student_care_agent_service,
        "export_agent_evaluation_summary_csv",
        lambda **kwargs: ("metric,value\ntotal_records,8", "student_care_evaluation_summary.csv"),
    )

    response = client.get("/api/student-care/evaluation-summary-export", headers=headers)
    assert response.status_code == 200
    assert "student_care_evaluation_summary.csv" in response.headers["content-disposition"]
    assert "total_records,8" in response.text


def test_teacher_can_view_student_care_evaluation_detail(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_api.student_care_agent_service,
        "get_agent_evaluation_detail",
        lambda **kwargs: {
            "code": 200,
            "msg": "success",
            "data": {
                "scene_breakdown": [
                    {
                        "scene": "social_isolation",
                        "review_count": 4,
                        "true_risk_count": 2,
                        "false_alarm_count": 1,
                        "unresolved_count": 1,
                        "agreement_rate": 0.75,
                        "avg_teacher_confidence": 4.0,
                        "severity_distribution": {"low": 1, "medium": 2, "high": 1, "unknown": 0},
                        "resolution_distribution": {"pending": 0, "in_progress": 1, "resolved": 2, "false_alarm": 1},
                    }
                ],
                "recent_reviews": [
                    {
                        "record_id": 99,
                        "student_id": 1,
                        "student_name": "李明",
                        "class_name": "高一(1)班",
                        "scene": "social_isolation",
                        "is_true_risk": "yes",
                        "severity": "medium",
                        "confidence_by_teacher": 4,
                        "resolution_status": "in_progress",
                        "system_level": "attention",
                        "teacher_notes": "已安排观察",
                        "confirmed_at": "2026-04-09 10:00:00",
                        "created_at": "2026-04-09 09:30:00",
                    }
                ],
            },
        },
    )

    response = client.get("/api/student-care/evaluation-detail", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["scene_breakdown"][0]["scene"] == "social_isolation"
    assert body["data"]["recent_reviews"][0]["student_name"] == "李明"


def test_profile_contains_bayes_results_for_safety():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    attendance_resp = client.post(
        "/api/attendance",
        json={
            "student_id": 1,
            "date": "2026-04-08",
            "status": "late",
            "remark": "脸上有淤青，班主任需要继续核实",
        },
        headers=headers,
    )
    assert attendance_resp.status_code == 200
    attendance_id = attendance_resp.json()["data"]["id"]

    behavior_resp = client.post(
        "/api/behavior-events",
        json={
            "student_id": 1,
            "event_type": "bullying",
            "event_level": "medium",
            "event_desc": "学生反映疑似被同学欺负",
            "occurred_at": "2026-04-08 09:20:00",
        },
        headers=headers,
    )
    assert behavior_resp.status_code == 200
    behavior_id = behavior_resp.json()["data"]["id"]

    try:
        response = client.get("/api/student-care/profile/1", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        profile = body["data"]["profile"]
        bayes = profile["bayes_results"]["safety"]
        assert bayes["enabled"] is True
        assert bayes["posterior"] > bayes["prior"]
        assert profile["safety_score"] >= profile["safety_linear_score"]
    finally:
        client.delete(f"/api/attendance/{attendance_id}", headers=headers)
        client.delete(f"/api/behavior-events/{behavior_id}", headers=headers)


def test_profile_contains_bayes_results_for_emotion():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    attendance_resp = client.post(
        "/api/attendance",
        json={
            "student_id": 1,
            "date": "2026-04-08",
            "status": "early_leave",
            "remark": "神情很担忧，需要继续关注",
        },
        headers=headers,
    )
    assert attendance_resp.status_code == 200
    attendance_id = attendance_resp.json()["data"]["id"]

    observation_resp = client.post(
        "/api/care-observations",
        json={
            "student_id": 1,
            "dimension": "emotion",
            "observation_type": "care_talk",
            "observation_level": "medium",
            "observed_at": "2026-04-08 14:20:00",
            "summary": "关怀谈话中学生表示近期情绪低落",
        },
        headers=headers,
    )
    assert observation_resp.status_code == 200
    observation_id = observation_resp.json()["data"]["id"]

    try:
        response = client.get("/api/student-care/profile/1", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        profile = body["data"]["profile"]
        bayes = profile["bayes_results"]["emotion"]
        assert bayes["enabled"] is True
        assert bayes["posterior"] > bayes["prior"]
        assert profile["emotion_score"] >= profile["emotion_linear_score"]
    finally:
        client.delete(f"/api/attendance/{attendance_id}", headers=headers)
        client.delete(f"/api/care-observations/{observation_id}", headers=headers)


def test_profile_contains_bayes_results_for_family():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    family_resp = client.post(
        "/api/family-contacts",
        json={
            "student_id": 1,
            "contact_type": "phone",
            "summary": "父亲打牌，不出去工作，对学生表现不耐烦",
        },
        headers=headers,
    )
    assert family_resp.status_code == 200
    family_id = family_resp.json()["data"]["id"]

    attendance_resp = client.post(
        "/api/attendance",
        json={
            "student_id": 1,
            "date": "2026-04-08",
            "status": "late",
            "remark": "因家庭临时安排迟到，需要继续关注",
        },
        headers=headers,
    )
    assert attendance_resp.status_code == 200
    attendance_id = attendance_resp.json()["data"]["id"]

    try:
        response = client.get("/api/student-care/profile/1", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        profile = body["data"]["profile"]
        bayes = profile["bayes_results"]["family"]
        assert bayes["enabled"] is True
        assert bayes["posterior"] > bayes["prior"]
        assert profile["family_score"] == profile["family_final_score"]
    finally:
        client.delete(f"/api/family-contacts/{family_id}", headers=headers)
        client.delete(f"/api/attendance/{attendance_id}", headers=headers)


def test_profile_includes_graph_signals(monkeypatch):
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
                "signal_text": "关系图谱中暂未形成稳定同伴连接",
                "signal_weight": 0.18,
                "source": "graph",
            }
        ],
    )

    response = client.get("/api/student-care/profile/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert any(item["source"] == "graph" for item in body["data"]["signals"])


def test_profile_graph_signal_updates_safety_bayes(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(student_care_graph_service, "enabled", True)
    monkeypatch.setattr(
        student_care_graph_service,
        "build_graph_signals",
        lambda db, student: [
            {
                "signal_type": "graph_conflict_cooccurrence",
                "dimension": "safety",
                "signal_text": "关系图谱显示该生所在班级近期存在多名学生卷入冲突/欺凌事件",
                "signal_weight": 0.22,
                "source": "graph",
            }
        ],
    )

    response = client.get("/api/student-care/profile/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    safety_bayes = body["data"]["profile"]["bayes_results"]["safety"]
    assert "graph_conflict_cooccurrence" in safety_bayes["evidence_keys"]
    assert safety_bayes["posterior"] > safety_bayes["prior"]


def test_admin_can_list_student_care_bayes_rules():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.get("/api/student-care/bayes-rules", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "rules" in body["data"]
    assert any(
        item["dimension"] == "safety" and item["evidence_key"] == "__base__"
        for item in body["data"]["rules"]
    )


def test_admin_can_override_student_care_bayes_rule():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    update_resp = client.put(
        "/api/student-care/bayes-rules/safety/__base__",
        json={
            "prior": 0.33,
            "blend_alpha": 0.55,
            "enabled": True,
            "description": "管理员调高安全维度先验",
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    update_body = update_resp.json()
    assert update_body["code"] == 200
    assert update_body["data"]["source"] == "database"
    assert update_body["data"]["prior"] == 0.33
    assert update_body["data"]["blend_alpha"] == 0.55

    list_resp = client.get("/api/student-care/bayes-rules", headers=headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    matched = next(
        item
        for item in list_body["data"]["rules"]
        if item["dimension"] == "safety" and item["evidence_key"] == "__base__"
    )
    assert matched["source"] == "database"
    assert matched["prior"] == 0.33
    assert matched["blend_alpha"] == 0.55


def test_admin_can_view_student_care_graph_health(monkeypatch):
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_graph_service,
        "healthcheck",
        lambda: {"enabled": True, "connected": True},
    )

    response = client.get("/api/student-care/graph-health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["connected"] is True


def test_teacher_can_view_student_care_graph_health(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_graph_service,
        "healthcheck",
        lambda: {"enabled": True, "connected": True},
    )

    response = client.get("/api/student-care/graph-health", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["enabled"] is True
    assert body["data"]["connected"] is True


def test_teacher_can_sync_student_care_graph(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_graph_service,
        "sync_student_graph",
        lambda db, student_id: {"enabled": True, "synced": True, "student_id": student_id},
    )

    response = client.post("/api/student-care/graph-sync/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["synced"] is True
    assert body["data"]["student_id"] == 1


def test_teacher_can_view_student_care_graph_view(monkeypatch):
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    monkeypatch.setattr(
        student_care_graph_service,
        "get_student_graph_view",
        lambda db, student_id: {
            "student_id": student_id,
            "window_days": 30,
            "nodes": [{"id": "student-1", "type": "student", "label": "李明", "focus": True}],
            "edges": [],
            "stats": {"student_count": 1, "peer_count": 0, "event_count": 0},
        },
    )

    response = client.get("/api/student-care/graph-view/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["student_id"] == 1
    assert body["data"]["stats"]["student_count"] == 1


def test_graph_view_only_shows_focus_student_behavior_events():
    client = create_client()
    token = login_as(client, username="wang_math", password="teacher123")
    headers = auth_headers(token)

    own_resp = client.post(
        "/api/behavior-events",
        json={
            "student_id": 1,
            "event_type": "discipline",
            "event_level": "medium",
            "event_desc": "focus student test event",
            "occurred_at": "2026-04-09 16:10:00",
        },
        headers=headers,
    )
    assert own_resp.status_code == 200
    own_id = own_resp.json()["data"]["id"]

    peer_resp = client.post(
        "/api/behavior-events",
        json={
            "student_id": 2,
            "event_type": "conflict",
            "event_level": "medium",
            "event_desc": "peer student test event",
            "occurred_at": "2026-04-09 16:20:00",
        },
        headers=headers,
    )
    assert peer_resp.status_code == 200
    peer_id = peer_resp.json()["data"]["id"]

    try:
        response = client.get("/api/student-care/graph-view/1", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        event_nodes = [item for item in body["data"]["nodes"] if item["type"] == "event"]
        assert event_nodes
        assert all(item.get("owner_student_id") == 1 for item in event_nodes)
    finally:
        client.delete(f"/api/behavior-events/{own_id}", headers=headers)
        client.delete(f"/api/behavior-events/{peer_id}", headers=headers)
