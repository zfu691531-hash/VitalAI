# -*- coding: utf-8 -*-
"""
AI生成历史记录表模型（ai_history）
==================================
存储用户使用AI工具生成的内容记录。
字段：id(主键), user_id(关联用户表,无外键), tool_type(功能类型),
      input_params(输入参数快照,JSON), content(生成内容),
      student_id(关联学生,可选), class_id(关联班级,可选),
      created_at, updated_at
"""

from sqlalchemy import BigInteger, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class AiHistory(Base, TimestampMixin):
    """AI历史记录表，tool_type 枚举值: comment/discipline/notice/rule_qa/score_diag/meeting/interview/group。"""

    __tablename__ = "ai_history"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_tool_type", "tool_type"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, comment="用户ID（关联user.id，无外键）",
    )
    tool_type: Mapped[str] = mapped_column(
        String(50),
        comment="功能类型（comment/discipline/notice/rule_qa/score_diag/meeting/interview/group）",
    )
    input_params: Mapped[dict | None] = mapped_column(
        JSON, comment="输入参数快照(JSON)，用于历史复用",
    )
    content: Mapped[str] = mapped_column(
        Text, comment="AI生成的内容",
    )
    student_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联学生ID（可选）",
    )
    class_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="关联班级ID（可选）",
    )
