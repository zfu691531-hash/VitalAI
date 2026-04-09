# -*- coding: utf-8 -*-
"""Rule feedback APIs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, require_role
from database.models.user import User
from schemas.rule_rag import RuleFeedbackReviewRequest
from services.rag import rule_feedback_service

router = APIRouter(prefix="/api/rule-feedback", tags=["rule-feedback"])


@router.get("")
def get_feedback_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_feedback_service.get_feedback_list(db, page, page_size, status)


@router.get("/{feedback_id}")
def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_feedback_service.get_feedback_detail(db, feedback_id)


@router.post("/{feedback_id}/adopt")
def adopt_feedback(
    feedback_id: int,
    payload: RuleFeedbackReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_feedback_service.adopt_feedback(db, current_user, feedback_id, payload)


@router.post("/{feedback_id}/revise-and-adopt")
def revise_and_adopt_feedback(
    feedback_id: int,
    payload: RuleFeedbackReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_feedback_service.adopt_feedback(db, current_user, feedback_id, payload)


@router.post("/{feedback_id}/reject")
def reject_feedback(
    feedback_id: int,
    payload: RuleFeedbackReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_feedback_service.reject_feedback(db, current_user, feedback_id, payload)
