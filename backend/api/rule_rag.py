# -*- coding: utf-8 -*-
"""Rule RAG APIs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from database.models.user import User
from schemas.rule_rag import RuleRagAskRequest, RuleRagFeedbackRequest
from services.rag import rule_rag_service

router = APIRouter(prefix="/api/rule-rag", tags=["rule-rag"])


@router.post("/ask")
async def ask_rule_rag(
    request: RuleRagAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await rule_rag_service.ask_rule_rag(db, current_user, request)


@router.post("/feedback")
def submit_rule_feedback(
    request: RuleRagFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rule_rag_service.submit_rule_feedback(db, current_user, request)


@router.get("/history")
def get_rule_rag_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return rule_rag_service.get_rule_rag_history(db, current_user, page, page_size)
