# -*- coding: utf-8 -*-
"""Student care profile model."""

from sqlalchemy import BigInteger, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareProfile(Base, TimestampMixin):
    __tablename__ = "student_care_profile"
    __table_args__ = (
        Index("idx_student_care_profile_student_id", "student_id"),
        Index("idx_student_care_profile_class_id", "class_id"),
        Index("idx_student_care_profile_risk_level", "risk_level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    student_id: Mapped[int] = mapped_column(BigInteger, unique=True, comment="学生ID")
    class_id: Mapped[int | None] = mapped_column(BigInteger, comment="班级ID")
    emotion_score: Mapped[float] = mapped_column(Float, default=0.0, comment="情绪状态风险")
    social_score: Mapped[float] = mapped_column(Float, default=0.0, comment="社交融入风险")
    safety_score: Mapped[float] = mapped_column(Float, default=0.0, comment="校园安全风险")
    family_score: Mapped[float] = mapped_column(Float, default=0.0, comment="家庭支持风险")
    study_score: Mapped[float] = mapped_column(Float, default=0.0, comment="学习压力风险")
    behavior_score: Mapped[float] = mapped_column(Float, default=0.0, comment="行为稳定风险")
    overall_risk: Mapped[float] = mapped_column(Float, default=0.0, comment="综合风险")
    risk_level: Mapped[str] = mapped_column(String(20), default="low", comment="风险等级")
    trend: Mapped[str] = mapped_column(String(20), default="steady", comment="趋势")
