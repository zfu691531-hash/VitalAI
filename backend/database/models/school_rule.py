# -*- coding: utf-8 -*-
"""
校规表模型（school_rule）
=========================
存储校规内容，供校规问答机器人使用，支持校务管理员后台更新。
字段：id(主键), category(校规分类), title(校规标题), content(校规正文),
      updated_by(最后更新人ID,无外键), created_at, updated_at
"""

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class SchoolRule(Base, TimestampMixin):
    """校规表，校规问答机器人的知识库数据源。"""

    __tablename__ = "school_rule"
    __table_args__ = (
        Index("idx_category", "category"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    category: Mapped[str] = mapped_column(
        String(50), comment="校规分类（如：考勤、行为规范、安全）",
    )
    title: Mapped[str] = mapped_column(
        String(200), comment="校规标题",
    )
    content: Mapped[str] = mapped_column(
        Text, comment="校规正文",
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, comment="最后更新人ID（关联user.id，无外键）",
    )
