# -*- coding: utf-8 -*-
"""Tag definition routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, require_role
from database.models.user import User
from schemas.student_tag_definition import TagDefinitionCreate, TagDefinitionUpdate
from services import tag_definition_service

router = APIRouter(prefix="/api/tag-definitions", tags=["标签字典"])


@router.get("")
def list_tag_definitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    scope_type: str | None = None,
    scope_value: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return tag_definition_service.list_definitions(
        db=db,
        page=page,
        page_size=page_size,
        scope_type=scope_type,
        scope_value=scope_value,
        keyword=keyword,
    )


@router.post("")
def create_tag_definition(
    data: TagDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return tag_definition_service.create_definition(db=db, current_user=current_user, data=data.model_dump())


@router.put("/{definition_id}")
def update_tag_definition(
    definition_id: int,
    data: TagDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return tag_definition_service.update_definition(db=db, record_id=definition_id, data=data.model_dump())


@router.delete("/{definition_id}")
def delete_tag_definition(
    definition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return tag_definition_service.delete_definition(db=db, record_id=definition_id)


@router.get("/available")
def get_available_tag_definitions(
    class_id: int | None = None,
    grade: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return tag_definition_service.get_available_definitions(db=db, class_id=class_id, grade=grade)
