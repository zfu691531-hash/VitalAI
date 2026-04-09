# -*- coding: utf-8 -*-
"""
违纪处理话术工具
================
根据违纪情况生成家校沟通话术，支持不同语气和对象。
"""

from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models.user import User
from services.ai.base import ai_client, save_history
from core.response import success_response
from utils.logger import logger


class DisciplineRequest(BaseModel):
    """违纪处理请求"""
    incident: str = Field(..., description="违纪事件描述")
    student_name: str = Field(..., description="学生姓名")
    mode: str = Field("温和", description="沟通模式：温和/严肃")
    target: str = Field("学生", description="沟通对象：学生/家长")


async def generate_discipline_script(
    db: Session,
    current_user: User,
    request: DisciplineRequest,
) -> dict:
    """
    生成违纪处理话术
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 生成结果
    """
    system_prompt = f"""你是一位经验丰富、善于沟通的班主任。
请针对学生的违纪行为，生成一份{request.mode}风格的家校沟通话术。
沟通对象是{request.target}。

要求：
1. 语气{"温和但坚定" if request.mode == "温和" else "严肃但不失关怀"}
2. 先肯定学生优点，再指出问题
3. 提出具体改进建议
4. {"让学生认识到错误并愿意改正" if request.target == "学生" else "让家长理解情况并配合教育"}
5. 字数200-300字"""

    user_prompt = f"""学生姓名：{request.student_name}
违纪事件：{request.incident}

请生成沟通话术。"""

    result = await ai_client.call(system_prompt, user_prompt)
    
    # 保存历史
    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="discipline",
        input_params=request.model_dump(),
        content=result,
    )
    
    return success_response(data={"script": result})
