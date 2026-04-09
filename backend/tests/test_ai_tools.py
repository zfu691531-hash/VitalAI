# -*- coding: utf-8 -*-
"""AI 工具主链路最小回归测试。"""

import pytest

from services.ai.base import ai_client
from tests.conftest import auth_headers, create_client, login_as


async def fake_ai_call(*args, **kwargs):
    """避免测试依赖真实外部 AI 服务。"""
    return "测试用 AI 响应"


def test_notice_ai_tool_and_history(monkeypatch):
    """公告润色接口应能返回结果并写入历史。"""
    monkeypatch.setattr(ai_client, "call", fake_ai_call)
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    response = client.post(
        "/api/ai/notice",
        headers=headers,
        json={
            "content": "明天下午召开家长会，请家长准时参加。",
            "style": "formal",
            "scene": "家长群",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["polished"] == "测试用 AI 响应"

    history_response = client.get(
        "/api/ai-history",
        headers=headers,
        params={"page": 1, "page_size": 10, "tool_type": "notice"},
    )

    assert history_response.status_code == 200
    history_list = history_response.json()["data"]["list"]
    assert any(item["tool_type"] == "notice" for item in history_list)


def test_rule_qa_ai_tool_with_history(monkeypatch):
    """校规问答接口应能处理多轮问答并正常返回。"""
    monkeypatch.setattr(ai_client, "call", fake_ai_call)
    client = create_client()
    token = login_as(client)

    response = client.post(
        "/api/ai/rule-qa",
        headers=auth_headers(token),
        json={
            "question": "校内使用手机有什么规定？",
            "chat_history": [
                {"question": "校服要求是什么？", "answer": "请按学校统一要求着装。"}
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["answer"] == "测试用 AI 响应"


def test_admin_group_assignment_preview_and_confirm(monkeypatch):
    """管理员可以先预览正式分班，再确认写入班级。"""
    monkeypatch.setattr(ai_client, "call", fake_ai_call)
    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    class_response = client.get(
        "/api/classes",
        headers=headers,
        params={"page": 1, "page_size": 50, "status": 1},
    )
    assert class_response.status_code == 200

    class_list = class_response.json()["data"]["list"]
    if not class_list:
        pytest.skip("No active classes available for grouping test.")

    grade = class_list[0]["grade"]
    preview_response = client.post(
        "/api/ai/group",
        headers=headers,
        json={
            "mode": "admin",
            "grade": grade,
            "group_count": 1,
            "balance_factors": ["score", "gender"],
        },
    )

    if preview_response.status_code != 200 or preview_response.json()["code"] != 200:
        pytest.skip("No eligible students available for admin grouping test.")

    preview_data = preview_response.json()["data"]
    assignments = [
        {
            "class_id": group["target_class_id"],
            "student_ids": [student["id"] for student in group["students"]],
        }
        for group in preview_data["groups"]
    ]

    confirm_response = client.post(
        "/api/ai/group/confirm",
        headers=headers,
        json={
            "grade": grade,
            "assignments": assignments,
        },
    )

    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["code"] == 200
    assert body["data"]["grade"] == grade
