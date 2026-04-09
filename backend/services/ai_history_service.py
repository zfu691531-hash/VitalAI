# -*- coding: utf-8 -*-
"""
AI历史服务模块
==============
查询、复用、删除AI生成历史记录。
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models.ai_history import AiHistory
from database.models.user import User
from core.response import success_response, error_response
from utils.logger import logger


def get_list(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    tool_type: Optional[str] = None,
) -> dict:
    """
    分页查询AI历史列表（仅当前用户）
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        page: 页码
        page_size: 每页数量
        tool_type: 工具类型筛选
    
    Returns:
        dict: 历史列表和总数
    """
    query = db.query(AiHistory).filter(AiHistory.user_id == current_user.id)
    
    if tool_type:
        query = query.filter(AiHistory.tool_type == tool_type)
    
    total = query.count()
    offset = (page - 1) * page_size
    
    histories = query.order_by(desc(AiHistory.created_at)).offset(offset).limit(page_size).all()
    
    list_data = []
    for h in histories:
        list_data.append({
            "id": h.id,
            "tool_type": h.tool_type,
            "input_params": h.input_params,
            "content": h.content[:200] + "..." if len(h.content) > 200 else h.content,
            "student_id": h.student_id,
            "class_id": h.class_id,
            "created_at": h.created_at,
        })
    
    return success_response(data={"list": list_data, "total": total})


def get_detail(
    db: Session,
    current_user: User,
    history_id: int,
) -> dict:
    """
    获取AI历史详情
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        history_id: 历史ID
    
    Returns:
        dict: 历史详情
    """
    history = db.query(AiHistory).filter(
        AiHistory.id == history_id,
        AiHistory.user_id == current_user.id,
    ).first()
    
    if not history:
        return error_response(msg="历史记录不存在或无权限访问")
    
    return success_response(data={
        "id": history.id,
        "tool_type": history.tool_type,
        "input_params": history.input_params,
        "content": history.content,
        "student_id": history.student_id,
        "class_id": history.class_id,
        "created_at": history.created_at,
        "updated_at": history.updated_at,
    })


def batch_delete(
    db: Session,
    current_user: User,
    history_ids: List[int],
) -> dict:
    """
    批量删除AI历史
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        history_ids: 历史ID列表
    
    Returns:
        dict: 操作结果
    """
    deleted = db.query(AiHistory).filter(
        AiHistory.id.in_(history_ids),
        AiHistory.user_id == current_user.id,
    ).delete(synchronize_session=False)
    
    db.commit()
    
    logger.info(f"批量删除AI历史: {deleted} 条")
    
    return success_response(msg=f"成功删除 {deleted} 条")
