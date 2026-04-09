# -*- coding: utf-8 -*-
"""Regression tests for personal AI assistant."""

from datetime import datetime
from zoneinfo import ZoneInfo

from database.connection import SessionLocal
from database.models.student_assistant_summary import StudentAssistantSummary
from services import assistant_service
from tests.conftest import auth_headers, create_client, login_as


async def fake_ai_call(*args, **kwargs):
    return "这是一个测试用的助理回复。"


def test_assistant_session_and_message_flow(monkeypatch):
    monkeypatch.setattr(assistant_service.ai_client, "call", fake_ai_call)

    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    session_response = client.get("/api/assistant/session", headers=headers)
    assert session_response.status_code == 200
    session_body = session_response.json()
    assert session_body["code"] == 200
    session_id = session_body["data"]["session_id"]
    assert session_id
    assert session_body["data"]["greeting"]

    send_response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"session_id": session_id, "content": "现在系统有多少学生和班级？"},
    )
    assert send_response.status_code == 200
    send_body = send_response.json()
    assert send_body["code"] == 200
    assert send_body["data"]["message"]["role"] == "assistant"
    assert "班级" in send_body["data"]["message"]["content"]

    session_again = client.get("/api/assistant/session", headers=headers)
    assert session_again.status_code == 200
    body_again = session_again.json()
    assert body_again["code"] == 200
    assert len(body_again["data"]["messages"]) >= 2


def test_assistant_stream_message_flow():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    with client.stream(
        "POST",
        "/api/assistant/message/stream",
        headers=headers,
        json={"content": "现在系统有多少学生和班级？"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"type": "status"' in body
    assert '"stage": "analyzing"' in body
    assert '"stage": "answering"' in body
    assert '"type": "chunk"' in body
    assert '"type": "done"' in body


def test_assistant_rule_rag_routing():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    with client.stream(
        "POST",
        "/api/assistant/message/stream",
        headers=headers,
        json={"content": "校规里手机被收走后多久可以拿回来？"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"tool": "rule_rag"' in body
    assert '校规知识库' in body
    assert '"type": "done"' in body


def test_assistant_daily_question_fallback(monkeypatch):
    async def fake_daily_call(*args, **kwargs):
        return "先深呼吸一下，给自己十分钟休息，再把今天最重要的一件事拆小去完成。"

    monkeypatch.setattr(assistant_service.ai_client, "call", fake_daily_call)

    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "最近压力有点大，怎么调整状态？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "llm_fallback"
    assert "先深呼吸" in body["data"]["message"]["content"]


def test_student_safety_disclosure_is_recorded_for_care_eval():
    client = create_client()
    token = login_as(client, username="stu_2024001", password="student123")
    headers = auth_headers(token)
    content = "我被人打了，受伤了，需要老师帮忙"

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": content},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "student_safety_disclosure"
    assert "老师" in body["data"]["message"]["content"]

    db = SessionLocal()
    try:
        record = (
            db.query(StudentAssistantSummary)
            .filter(StudentAssistantSummary.summary_text.contains(content))
            .order_by(StudentAssistantSummary.id.desc())
            .first()
        )
        assert record is not None
        signals = (record.signals_json or {}).get("signals") or []
        assert any(item.get("dimension") == "safety" for item in signals)
        assert any(item.get("dimension") == "emotion" for item in signals)
        db.delete(record)
        db.commit()
    finally:
        db.close()


def test_assistant_class_scope_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级1班现在有多少学生？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "class_scope"
    assert "2024级1班" in body["data"]["message"]["content"]


def test_assistant_student_detail_lookup():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "帮我看看学生李明的信息"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "student_detail"
    assert "学生" in body["data"]["message"]["content"]


def test_assistant_grade_score_scope_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级的成绩情况怎么样？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "score_scope"
    assert "2024级" in body["data"]["message"]["content"]


def test_assistant_teacher_class_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "王建国负责哪些班级？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "teacher_scope"
    assert "王建国" in body["data"]["message"]["content"]


def test_assistant_student_score_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "李明的成绩情况怎么样？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "score_lookup"
    assert "李明" in body["data"]["message"]["content"]


def test_assistant_class_composition_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级1班的班主任和班级构成是什么？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "class_scope"
    assert "班主任" in body["data"]["message"]["content"]


def test_assistant_grade_unassigned_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级还有多少待分班学生？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "class_scope"
    assert "待分班" in body["data"]["message"]["content"]


def test_assistant_student_subject_score_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "李明数学成绩怎么样？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "score_lookup"
    assert "数学" in body["data"]["message"]["content"]


def test_assistant_grade_exam_batch_score_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级期中成绩情况怎么样？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "score_scope"
    assert "期中" in body["data"]["message"]["content"]


def test_assistant_class_student_list_detail():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "2024级1班有哪些学生？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "class_scope"
    assert "班内有" in body["data"]["message"]["content"]


def test_assistant_datetime_tool():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "今天几号？"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "datetime"
    current_year = str(datetime.now(ZoneInfo("Asia/Shanghai")).year)
    assert current_year in body["data"]["message"]["content"]


def test_assistant_web_search_routing(monkeypatch):
    async def fake_search(query: str):
        return {
            "summary": "我查到今天北京天气多云转晴，最高气温 22 度。",
            "sources": [{"title": "天气结果", "snippet": "北京天气多云转晴", "url": "https://example.com"}],
        }

    monkeypatch.setattr(assistant_service, "search_web", fake_search)

    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "帮我联网查一下今天北京天气"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "web_search"
    assert "天气" in body["data"]["message"]["content"]
def test_assistant_unavailable_capability_guard():
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"content": "帮我查一下今天的课表"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["message"]["meta"]["tool"] == "capability_guard"
    assert "还没有接入课表" in body["data"]["message"]["content"]


def test_assistant_clear_session_history(monkeypatch):
    monkeypatch.setattr(assistant_service.ai_client, "call", fake_ai_call)

    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    session_response = client.get("/api/assistant/session", headers=headers)
    session_id = session_response.json()["data"]["session_id"]

    send_response = client.post(
        "/api/assistant/message",
        headers=headers,
        json={"session_id": session_id, "content": "先记住这句话"},
    )
    assert send_response.status_code == 200

    clear_response = client.post(
        "/api/assistant/session/clear",
        headers=headers,
        json={"session_id": session_id},
    )
    assert clear_response.status_code == 200
    clear_body = clear_response.json()
    assert clear_body["code"] == 200
    assert clear_body["data"]["session_id"] == session_id
    assert clear_body["data"]["messages"] == []
    assert clear_body["data"]["greeting"]
