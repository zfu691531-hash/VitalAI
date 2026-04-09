# -*- coding: utf-8 -*-
"""Rule KB APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db, require_role
from database.models.user import User
from services.rag import rule_kb_service

router = APIRouter(prefix="/api/rule-kb", tags=["rule-kb"])


@router.post("/reindex/{rule_id}")
def reindex_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_kb_service.rebuild_rule_index(db, rule_id)


@router.post("/reindex-all")
def reindex_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return rule_kb_service.rebuild_all_indexes(db)
