from __future__ import annotations

# -*- coding: utf-8 -*-
"""Student tag review model."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base, TimestampMixin


class StudentTagReview(Base, TimestampMixin):
    __tablename__ = "student_tag_review"
    __table_args__ = (
        Index("idx_student_tag_review_status", "status"),
        Index("idx_student_tag_review_tag", "tag_text"),
        Index("idx_student_tag_review_student", "student_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    tag_text: Mapped[str] = mapped_column(String(50), comment="Tag text")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/approved/rejected")

    student_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="related student id")
    class_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="related class id")
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="related grade")
    source: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="teacher_input/ai_detected")

    suggested_scope_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="school/grade/class")
    suggested_scope_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="scope value")
    suggested_polarity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="positive/neutral/negative")
    suggested_dimension: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="dimension")
    suggested_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="weight")
    suggested_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="description")
    suggestion_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="note from auto analysis")

    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="created by user id")
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="reviewed by user id")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="reviewed at")
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="review note")
