# -*- coding: utf-8 -*-
"""Student care risk signal model."""

from sqlalchemy import BigInteger, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareSignal(Base, TimestampMixin):
    __tablename__ = "student_care_signal"
    __table_args__ = (
        Index("idx_student_care_signal_student_id", "student_id"),
        Index("idx_student_care_signal_class_id", "class_id"),
        Index("idx_student_care_signal_dimension", "dimension"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="学生ID")
    class_id: Mapped[int | None] = mapped_column(BigInteger, comment="班级ID")
    signal_type: Mapped[str] = mapped_column(String(50), comment="信号类型")
    dimension: Mapped[str] = mapped_column(String(30), comment="维度")
    signal_text: Mapped[str] = mapped_column(Text, comment="信号内容")
    signal_weight: Mapped[float] = mapped_column(Float, default=0.0, comment="信号权重")
    source: Mapped[str] = mapped_column(String(30), comment="来源")
