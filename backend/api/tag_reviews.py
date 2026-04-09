# -*- coding: utf-8 -*-
"""Tag review routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, require_role
from database.models.user import User
from schemas.student_tag_review import TagReviewApprove, TagReviewReject
from services import tag_review_service

router = APIRouter(prefix="/api/tag-reviews", tags=["标签审核"])


@router.get("")
def list_tag_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str | None = None,
    keyword: str | None = None,
    class_id: int | None = None,
    grade: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    return tag_review_service.list_reviews(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        keyword=keyword,
        class_id=class_id,
        grade=grade,
    )


@router.post("/{review_id}/approve")
def approve_tag_review(
    review_id: int,
    data: TagReviewApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    return tag_review_service.approve_review(db=db, current_user=current_user, review_id=review_id, data=data.model_dump())


@router.post("/{review_id}/reject")
def reject_tag_review(
    review_id: int,
    data: TagReviewReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    return tag_review_service.reject_review(db=db, current_user=current_user, review_id=review_id, data=data.model_dump())
