# -*- coding: utf-8 -*-
"""
成绩表模型（score）
====================
存储学生成绩信息。
字段：id(主键), student_id(关联学生表,无外键), class_id(关联班级表,无外键),
      exam_batch(考试批次,如期中/期末), subject(科目), score(分数),
      created_at, updated_at

注意：score 是 MySQL 保留字（需反引号），但作为 Python 属性名合法。
"""

from sqlalchemy import BigInteger, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class Score(Base, TimestampMixin):
    """成绩表。"""

    __tablename__ = "score"
    __table_args__ = (
        Index("idx_student_id", "student_id"),
        Index("idx_class_id", "class_id"),
        Index("idx_exam_batch", "exam_batch"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, comment="学生ID（关联student.id，无外键）",
    )
    class_id: Mapped[int] = mapped_column(
        BigInteger, comment="班级ID（关联class.id，无外键）",
    )
    exam_batch: Mapped[str] = mapped_column(
        String(50), comment="考试批次（如期中、期末）",
    )
    subject: Mapped[str] = mapped_column(
        String(50), comment="科目",
    )
    score: Mapped[float] = mapped_column(
        Numeric(5, 2), comment="分数（0-100）",
    )
