# -*- coding: utf-8 -*-
"""
班会活动策划工具
================
生成班会活动方案，支持不同主题和年级。
"""

from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models.user import User
from services.ai.base import ai_client, save_history
from core.response import success_response
from utils.logger import logger


class MeetingRequest(BaseModel):
    """班会策划请求"""
    theme: str = Field(..., description="班会主题")
    grade: str = Field(..., description="年级")
    duration: int = Field(45, description="时长（分钟）")
    participants: str = Field("全班学生", description="参与对象")


async def plan_meeting(
    db: Session,
    current_user: User,
    request: MeetingRequest,
) -> dict:
    """
    策划班会活动
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 策划方案
    """
    system_prompt = f"""你是一位经验丰富的班主任，擅长策划班会活动。
请根据以下信息，设计一份完整的班会活动方案。

要求：
1. 结构完整：主题、目标、流程、注意事项
2. 流程详细：每个环节的时间分配和具体内容
3. 互动性强：设计学生参与环节
4. 时长控制：总时长约{request.duration}分钟
5. 适合{request.grade}学生特点
6. 格式清晰，便于执行"""

    user_prompt = f"""班会主题：{request.theme}
年级：{request.grade}
时长：{request.duration}分钟
参与对象：{request.participants}

请设计班会活动方案："""

    result = await ai_client.call(system_prompt, user_prompt, max_tokens=3000)
    
    # 保存历史
    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="meeting",
        input_params=request.model_dump(),
        content=result,
    )
    
    return success_response(data={"plan": result})
