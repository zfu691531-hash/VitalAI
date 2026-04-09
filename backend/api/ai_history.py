# -*- coding: utf-8 -*-
"""
AI历史记录路由
===============
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user
from database.models.user import User
from schemas.common import BatchDeleteRequest
from services import ai_history_service

router = APIRouter(prefix="/api/ai-history", tags=["AI历史"])


@router.get("")
def get_ai_history_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    tool_type: Optional[str] = Query(None, description="工具类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询AI历史列表（仅当前用户）"""
    return ai_history_service.get_list(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        tool_type=tool_type,
    )


@router.get("/{history_id}")
def get_ai_history_detail(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取AI历史详情"""
    return ai_history_service.get_detail(
        db=db,
        current_user=current_user,
        history_id=history_id,
    )


@router.post("/batch-delete")
def batch_delete_ai_history(
    data: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除AI历史"""
    return ai_history_service.batch_delete(
        db=db,
        current_user=current_user,
        history_ids=data.ids,
    )
