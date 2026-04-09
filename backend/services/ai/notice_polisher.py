# -*- coding: utf-8 -*-
"""
公告润色工具
============
对教师撰写的公告进行润色，支持不同风格和场景。
"""

from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models.user import User
from services.ai.base import ai_client, save_history
from core.response import success_response
from utils.logger import logger


class NoticeRequest(BaseModel):
    """公告润色请求"""
    content: str = Field(..., description="原始公告内容")
    style: str = Field("正式", description="润色风格：正式/亲切/简洁")
    scene: str = Field("家长群", description="使用场景：家长群/班级群/学校公告栏")
    class_id: Optional[int] = Field(None, description="班级ID（可选）")


async def polish_notice(
    db: Session,
    current_user: User,
    request: NoticeRequest,
) -> dict:
    """
    润色公告
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 润色结果
    """
    system_prompt = f"""你是一位文字功底深厚的行政人员。
请对以下公告进行润色，风格要求：{request.style}。
使用场景：{request.scene}。

要求：
1. {"语言正式、规范，适合官方发布" if request.style == "正式" else "语言亲切、易懂，贴近家长和学生" if request.style == "亲切" else "语言简洁、精炼，突出重点"}
2. 纠正语病和错别字
3. 调整段落结构，增强可读性
4. 保持原意不变
5. 字数与原文相近"""

    user_prompt = f"""原始公告：
{request.content}

请润色后的公告："""

    result = await ai_client.call(system_prompt, user_prompt)
    
    # 保存历史
    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="notice",
        input_params=request.model_dump(),
        content=result,
        class_id=request.class_id,
    )
    
    return success_response(data={"polished": result})
