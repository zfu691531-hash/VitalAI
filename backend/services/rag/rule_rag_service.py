# -*- coding: utf-8 -*-
"""Rule RAG ask/feedback services."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.rule_qa_feedback import RuleQaFeedback
from database.models.rule_qa_record import RuleQaRecord
from database.models.user import User
from schemas.rule_rag import RuleRagAskRequest, RuleRagFeedbackRequest
from services.ai.base import ai_client
from services.rag.hybrid_retriever import hybrid_search
from services.rag.schema_guard import ensure_rule_rag_schema
from utils.logger import logger


async def ask_rule_rag(db: Session, current_user: User, request: RuleRagAskRequest) -> dict:
    ensure_rule_rag_schema()
    trace_id = uuid.uuid4().hex
    retrieved = hybrid_search(db=db, query=request.question, top_k=5)

    if retrieved:
        knowledge = "\n\n".join(
            f"[片段{index + 1}] rule_id={item['rule_id']}\n{item['chunk_text']}"
            for index, item in enumerate(retrieved)
        )
        system_prompt = (
            "你是校园校规问答助手。请严格依据给定的校规片段作答，不要编造不存在的规则。"
            "如果信息不足，请明确说明。"
        )
        user_prompt = (
            f"{_format_history(request.chat_history or [])}\n当前问题：{request.question}\n\n"
            f"参考校规片段：\n{knowledge}\n\n请用清晰、友好的语气作答。"
        )
        answer = await ai_client.call(system_prompt, user_prompt, temperature=0.2, max_tokens=1200)
    else:
        answer = "当前知识库没有命中足够相关的校规内容，建议联系管理员补充规则。"

    sources = [
        {
            "rule_id": item["rule_id"],
            "chunk_id": item["chunk_id"],
            "chunk_text": item["chunk_text"],
            "scores": item["scores"],
        }
        for item in retrieved
    ]

    record = RuleQaRecord(
        user_id=current_user.id,
        question=request.question,
        answer=answer,
        retrieved_chunks_json=sources,
        retrieval_meta_json={
            "strategy": "hybrid",
            "components": ["bm25", "sparse", "dense"],
            "result_count": len(sources),
        },
        trace_id=trace_id,
        model_name=getattr(ai_client, "model", None),
        status="success",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info("rule rag answer saved: record=%s", record.id)
    return success_response(
        data={
            "qa_record_id": record.id,
            "answer": answer,
            "trace_id": trace_id,
            "sources": sources,
        }
    )


def submit_rule_feedback(db: Session, current_user: User, request: RuleRagFeedbackRequest) -> dict:
    ensure_rule_rag_schema()
    record = db.query(RuleQaRecord).filter(RuleQaRecord.id == request.qa_record_id).first()
    if not record:
        return error_response(msg="问答记录不存在")
    if request.rating not in {"up", "down"}:
        return error_response(msg="反馈类型仅支持 up 或 down")

    feedback = RuleQaFeedback(
        qa_record_id=request.qa_record_id,
        user_id=current_user.id,
        rating=request.rating,
        improvement_reason=request.improvement_reason,
        suggested_answer=request.suggested_answer,
        status="pending",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return success_response(msg="反馈已提交", data={"id": feedback.id})


def get_rule_rag_history(db: Session, current_user: User, page: int, page_size: int) -> dict:
    ensure_rule_rag_schema()
    query = db.query(RuleQaRecord)
    if current_user.role != "admin":
        query = query.filter(RuleQaRecord.user_id == current_user.id)

    total = query.count()
    rows = (
        query.order_by(RuleQaRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(
        data={
            "list": [
                {
                    "id": item.id,
                    "question": item.question,
                    "answer": item.answer,
                    "trace_id": item.trace_id,
                    "status": item.status,
                    "created_at": item.created_at,
                }
                for item in rows
            ],
            "total": total,
        }
    )


def _format_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return ""
    rows = []
    for item in chat_history[-5:]:
        question = item.get("question") or item.get("user") or ""
        answer = item.get("answer") or item.get("assistant") or ""
        if question or answer:
            rows.append(f"历史问：{question}\n历史答：{answer}")
    return "\n\n".join(rows)
