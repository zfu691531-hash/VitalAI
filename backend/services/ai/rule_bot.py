# -*- coding: utf-8 -*-
"""
校规问答工具
============
基于校规知识库回答问题，支持多轮对话。
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models.user import User
from database.models.school_rule import SchoolRule
from services.ai.base import ai_client, save_history
from core.response import success_response
from utils.logger import logger


class RuleQARequest(BaseModel):
    """校规问答请求"""
    question: str = Field(..., description="用户问题")
    chat_history: Optional[List[dict]] = Field(None, description="对话历史")


async def answer_rule_question(
    db: Session,
    current_user: User,
    request: RuleQARequest,
) -> dict:
    """
    回答校规问题
    
    Args:
        db: 数据库会话
        current_user: 当前用户
        request: 请求参数
    
    Returns:
        dict: 回答结果
    """
    # 查询所有校规
    rules = db.query(SchoolRule).all()
    
    # 构建知识库
    knowledge = ""
    for rule in rules:
        knowledge += f"【{rule.title}】\n{rule.content}\n\n"
    
    # 构建对话历史
    history_text = ""
    if request.chat_history:
        for msg in request.chat_history[-5:]:  # 最近5轮
            history_text += f"问：{msg.get('question', '')}\n答：{msg.get('answer', '')}\n\n"
    
    system_prompt = f"""你是学校的校规解答助手。
请根据以下校规知识库回答学生和家长的疑问。

校规知识库：
{knowledge}

要求：
1. 只回答与校规相关的问题
2. 引用具体条款时要准确
3. 语气友好、耐心
4. 如果问题超出校规范围，请诚实告知"""

    user_prompt = f"""{f"对话历史：\n{history_text}\n" if history_text else ""}当前问题：{request.question}

请回答："""

    result = await ai_client.call(system_prompt, user_prompt)
    
    # 保存历史
    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="rule_qa",
        input_params=request.model_dump(),
        content=result,
    )
    
    return success_response(data={"answer": result})
