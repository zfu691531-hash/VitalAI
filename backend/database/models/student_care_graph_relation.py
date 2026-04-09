# -*- coding: utf-8 -*-
"""Manual graph relation model for student care."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareGraphRelation(Base, TimestampMixin):
    __tablename__ = "student_care_graph_relation"
    __table_args__ = (
        Index("idx_student_care_graph_relation_student_id", "student_id"),
        Index("idx_student_care_graph_relation_target_student_id", "target_student_id"),
        Index("idx_student_care_graph_relation_target_type", "target_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Focus student id")
    target_type: Mapped[str] = mapped_column(String(20), comment="student/event")
    target_student_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Target student id")
    relation_type: Mapped[str] = mapped_column(String(32), comment="Relation type")
    dimension: Mapped[str] = mapped_column(String(30), comment="Risk dimension")
    relation_level: Mapped[str] = mapped_column(String(20), comment="low/medium/high")
    summary: Mapped[str] = mapped_column(Text, comment="Relation summary")
    event_title: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="Manual event title")
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Occurred at")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="Creator user id")
