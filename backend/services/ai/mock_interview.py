# -*- coding: utf-8 -*-
"""
模拟面试工具
============
模拟面试场景，支持多轮对话。
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models.user import User
from database.models.student import Student
from services.ai.base import ai_client, save_history
from core.response import success_response, error_response
from utils.logger import logger


class InterviewRequest(BaseModel):
    """模拟面试请求"""
    interview_type: str = Field("自主招生", description="面试类型：自主招生/社团招新/班干部竞选")
    student_id: Optional[int] = Field(None, description="学生ID")
    answer: Optional[str] = Field(None, description="学生回答（多轮对话时使用）")
    chat_history: Optional[List[dict]] = Field(None, description="对话历史")


async def mock_interview(
    db: Session,
    current_user: User,
    request: InterviewRequest,
) -> dict:
    """
    模拟面试
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 面试结果
    """
    # 获取学生信息
    student_name = "同学"
    student_info = ""
    if request.student_id:
        student = db.query(Student).filter(Student.id == request.student_id).first()
        if student:
            student_name = student.name
            student_info = f"特长：{student.specialty or '无'}，标签：{student.tags or '无'}"
    
    # 构建对话历史
    history_text = ""
    if request.chat_history:
        for msg in request.chat_history[-5:]:
            history_text += f"面试官：{msg.get('question', '')}\n学生：{msg.get('answer', '')}\n\n"
    
    # 第一轮：提问
    if not request.answer:
        system_prompt = f"""你是一位专业的{request.interview_type}面试官。
请根据面试类型和学生信息，提出第一个问题。

要求：
1. 问题要有针对性，符合{request.interview_type}特点
2. 语气友好但专业
3. 一次只问一个问题
4. 学生信息：{student_name}，{student_info}"""

        user_prompt = "请开始面试，提出第一个问题。"
    
    # 后续轮次：点评+追问
    else:
        system_prompt = f"""你是一位专业的{request.interview_type}面试官。
学生刚刚回答了你的问题，请先点评回答，然后提出下一个问题。

对话历史：
{history_text}

学生刚刚回答：{request.answer}

要求：
1. 先对回答进行简短点评（优点和不足）
2. 然后提出下一个相关问题
3. 如果已进行3轮以上，可以结束面试并给出总体评价
4. 语气友好但专业"""

        user_prompt = "请点评并继续。"
    
    result = await ai_client.call(system_prompt, user_prompt)
    
    # 判断是否结束
    is_finished = "面试结束" in result or len(request.chat_history or []) >= 5
    
    # 保存历史（结束时）
    if is_finished:
        save_history(
            db=db,
            user_id=current_user.id,
            tool_type="interview",
            input_params=request.model_dump(),
            content=result,
            student_id=request.student_id,
        )
    
    return success_response(data={
        "content": result,
        "is_finished": is_finished,
    })
