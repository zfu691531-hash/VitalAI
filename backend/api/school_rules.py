# -*- coding: utf-8 -*-
"""
校规管理路由
=============
仅admin可操作。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user, require_role
from database.models.user import User
from schemas.school_rule import SchoolRuleCreate, SchoolRuleUpdate
from services import school_rule_service

router = APIRouter(prefix="/api/school-rules", tags=["校规管理"])


@router.get("")
def get_school_rule_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询校规列表"""
    return school_rule_service.get_list(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
    )


@router.get("/categories")
def get_school_rule_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有分类"""
    return school_rule_service.get_categories(db=db)


@router.post("")
def create_school_rule(
    data: SchoolRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """新增校规（仅admin）"""
    return school_rule_service.create(
        db=db,
        current_user=current_user,
        category=data.category,
        title=data.title,
        content=data.content,
    )


@router.put("/{rule_id}")
def update_school_rule(
    rule_id: int,
    data: SchoolRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """更新校规（仅admin）"""
    return school_rule_service.update(
        db=db,
        current_user=current_user,
        rule_id=rule_id,
        category=data.category,
        title=data.title,
        content=data.content,
    )


@router.delete("/{rule_id}")
def delete_school_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除校规（仅admin）"""
    return school_rule_service.delete(db=db, rule_id=rule_id)
