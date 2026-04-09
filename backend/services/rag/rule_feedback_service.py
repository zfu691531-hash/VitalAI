# -*- coding: utf-8 -*-
"""Rule feedback review service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.rule_qa_feedback import RuleQaFeedback
from database.models.rule_qa_record import RuleQaRecord
from database.models.school_rule import SchoolRule
from database.models.user import User
from schemas.rule_rag import RuleFeedbackReviewRequest
from services.rag.rule_kb_service import rebuild_rule_index
from services.rag.schema_guard import ensure_rule_rag_schema


def get_feedback_list(db: Session, page: int, page_size: int, status: str | None = None) -> dict:
    ensure_rule_rag_schema()
    query = db.query(RuleQaFeedback, RuleQaRecord).join(
        RuleQaRecord, RuleQaFeedback.qa_record_id == RuleQaRecord.id
    )
    if status:
        query = query.filter(RuleQaFeedback.status == status)

    total = query.count()
    rows = (
        query.order_by(RuleQaFeedback.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(
        data={
            "list": [
                {
                    "id": feedback.id,
                    "qa_record_id": feedback.qa_record_id,
                    "rating": feedback.rating,
                    "improvement_reason": feedback.improvement_reason,
                    "suggested_answer": feedback.suggested_answer,
                    "status": feedback.status,
                    "question": record.question,
                    "answer": record.answer,
                    "created_at": feedback.created_at,
                }
                for feedback, record in rows
            ],
            "total": total,
        }
    )


def get_feedback_detail(db: Session, feedback_id: int) -> dict:
    ensure_rule_rag_schema()
    row = (
        db.query(RuleQaFeedback, RuleQaRecord)
        .join(RuleQaRecord, RuleQaFeedback.qa_record_id == RuleQaRecord.id)
        .filter(RuleQaFeedback.id == feedback_id)
        .first()
    )
    if not row:
        return error_response(msg="反馈不存在")
    feedback, record = row
    return success_response(
        data={
            "id": feedback.id,
            "qa_record_id": feedback.qa_record_id,
            "rating": feedback.rating,
            "improvement_reason": feedback.improvement_reason,
            "suggested_answer": feedback.suggested_answer,
            "status": feedback.status,
            "review_note": feedback.review_note,
            "reviewed_by": feedback.reviewed_by,
            "question": record.question,
            "answer": record.answer,
            "sources": record.retrieved_chunks_json or [],
            "trace_id": record.trace_id,
        }
    )


def adopt_feedback(db: Session, current_user: User, feedback_id: int, payload: RuleFeedbackReviewRequest) -> dict:
    ensure_rule_rag_schema()
    row = (
        db.query(RuleQaFeedback, RuleQaRecord)
        .join(RuleQaRecord, RuleQaFeedback.qa_record_id == RuleQaRecord.id)
        .filter(RuleQaFeedback.id == feedback_id)
        .first()
    )
    if not row:
        return error_response(msg="反馈不存在")
    feedback, record = row

    target_rule_id = _pick_target_rule_id(record.retrieved_chunks_json or [])
    if not target_rule_id:
        return error_response(msg="没有找到可更新的校规来源")

    rule = db.query(SchoolRule).filter(SchoolRule.id == target_rule_id).first()
    if not rule:
        return error_response(msg="目标校规不存在")

    revised = bool(payload.revised_content or payload.revised_title or payload.revised_category)
    if payload.revised_title:
        rule.title = payload.revised_title
    if payload.revised_category:
        rule.category = payload.revised_category
    if payload.revised_content:
        rule.content = payload.revised_content
    if not revised:
        additions = []
        if feedback.improvement_reason:
            additions.append(f"用户反馈：{feedback.improvement_reason}")
        if feedback.suggested_answer:
            additions.append(f"建议答案：{feedback.suggested_answer}")
        if additions:
            rule.content = f"{rule.content}\n\n" + "\n".join(additions)

    rule.updated_by = current_user.id
    feedback.status = "revised" if revised else "adopted"
    feedback.review_note = payload.review_note
    feedback.reviewed_by = current_user.id
    db.commit()

    rebuild = rebuild_rule_index(db, rule.id)
    return success_response(
        msg="反馈已采纳",
        data={"feedback_id": feedback.id, "rule_id": rule.id, "reindex": rebuild.get("data")},
    )


def reject_feedback(db: Session, current_user: User, feedback_id: int, payload: RuleFeedbackReviewRequest) -> dict:
    ensure_rule_rag_schema()
    feedback = db.query(RuleQaFeedback).filter(RuleQaFeedback.id == feedback_id).first()
    if not feedback:
        return error_response(msg="反馈不存在")
    feedback.status = "rejected"
    feedback.review_note = payload.review_note
    feedback.reviewed_by = current_user.id
    db.commit()
    return success_response(msg="反馈已驳回")


def _pick_target_rule_id(sources: list[dict]) -> int | None:
    if not sources:
        return None
    return sources[0].get("rule_id")
