# -*- coding: utf-8 -*-
"""Regression tests for new rule RAG feedback loop."""

from services.ai.base import ai_client
from tests.conftest import auth_headers, create_client, login_as


async def fake_ai_call(*args, **kwargs):
    return "测试用新版校规问答回复"


def fake_embed_texts(texts, model_name=None):
    return [[0.001 * (index + 1) for index in range(1024)] for _ in texts]


def test_rule_rag_feedback_adopt_flow(monkeypatch):
    monkeypatch.setattr(ai_client, "call", fake_ai_call)
    monkeypatch.setattr(ai_client, "embed_texts", fake_embed_texts)

    client = create_client()
    token = login_as(client)
    headers = auth_headers(token)

    ask_response = client.post(
        "/api/rule-rag/ask",
        headers=headers,
        json={
            "question": "手机被收走后多久可以拿回来？",
            "chat_history": [],
        },
    )
    assert ask_response.status_code == 200
    ask_body = ask_response.json()
    assert ask_body["code"] == 200
    qa_record_id = ask_body["data"]["qa_record_id"]

    feedback_response = client.post(
        "/api/rule-rag/feedback",
        headers=headers,
        json={
            "qa_record_id": qa_record_id,
            "rating": "down",
            "improvement_reason": "建议明确首次违规的领取时间",
            "suggested_answer": "首次违规由家长在当周周五17:00后到校领取。",
        },
    )
    assert feedback_response.status_code == 200
    feedback_body = feedback_response.json()
    assert feedback_body["code"] == 200
    feedback_id = feedback_body["data"]["id"]

    detail_response = client.get(f"/api/rule-feedback/{feedback_id}", headers=headers)
    assert detail_response.status_code == 200
    detail_body = detail_response.json()
    assert detail_body["code"] == 200
    assert detail_body["data"]["sources"]

    adopt_response = client.post(
        f"/api/rule-feedback/{feedback_id}/adopt",
        headers=headers,
        json={"review_note": "已采纳并触发知识库重建"},
    )
    assert adopt_response.status_code == 200
    adopt_body = adopt_response.json()
    assert adopt_body["code"] == 200
    assert adopt_body["data"]["reindex"]["chunk_count"] >= 1

    list_response = client.get(
        "/api/rule-feedback",
        headers=headers,
        params={"page": 1, "page_size": 10, "status": "adopted"},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["code"] == 200
    assert any(item["id"] == feedback_id for item in list_body["data"]["list"])
