# -*- coding: utf-8 -*-
"""
教师表模型（teacher）
=====================
存储教师详细信息。
字段：id(主键), name(姓名), subject(任教科目), title(职务:班主任/普通教师),
      class_ids(绑定班级ID列表,逗号分隔,无外键),
      created_at, updated_at
"""

from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class Teacher(Base, TimestampMixin):
    """教师表，class_ids 使用逗号分隔字符串存储绑定班级。"""

    __tablename__ = "teacher"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    name: Mapped[str] = mapped_column(
        String(50), comment="姓名",
    )
    subject: Mapped[str | None] = mapped_column(
        String(50), comment="任教科目",
    )
    title: Mapped[str] = mapped_column(
        Enum("head_teacher", "normal"),
        comment="职务: head_teacher-班主任, normal-普通教师",
    )
    class_ids: Mapped[str | None] = mapped_column(
        String(500), comment="绑定班级ID列表，逗号分隔（关联class.id，无外键）",
    )
