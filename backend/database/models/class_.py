# -*- coding: utf-8 -*-
"""
班级表模型（class）
====================
存储班级信息。
字段：id(主键), grade(年级), name(班级名,唯一), head_teacher_id(班主任ID),
      max_count(人数上限), current_count(当前人数), status(状态:1-在读/0-已毕业),
      created_at, updated_at
"""

from sqlalchemy import BigInteger, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class Class(Base, TimestampMixin):
    """班级表，current_count 由业务层维护。"""

    __tablename__ = "class"
    __table_args__ = (
        Index("idx_grade", "grade"),
        Index("idx_head_teacher_id", "head_teacher_id"),
        Index("idx_status", "status"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    grade: Mapped[str] = mapped_column(
        String(20), comment="年级（如：2024级）",
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, comment="班级名称，唯一（如：2024级1班）",
    )
    head_teacher_id: Mapped[int | None] = mapped_column(
        BigInteger, comment="班主任ID（关联teacher.id，无外键）",
    )
    max_count: Mapped[int] = mapped_column(
        Integer, comment="人数上限",
    )
    current_count: Mapped[int] = mapped_column(
        Integer, comment="当前人数（业务层维护）",
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, comment="状态: 1-在读, 0-已毕业",
    )
