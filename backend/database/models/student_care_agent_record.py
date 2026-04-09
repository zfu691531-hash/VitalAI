from __future__ import annotations

# -*- coding: utf-8 -*-
"""Student care agent evaluation record model."""

from typing import Optional

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareAgentRecord(Base, TimestampMixin):
    __tablename__ = "student_care_agent_record"
    __table_args__ = (
        Index("idx_student_care_agent_record_student_id", "student_id"),
        Index("idx_student_care_agent_record_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    model_name: Mapped[str] = mapped_column(String(100), comment="Model name")
    timeout_seconds: Mapped[int] = mapped_column(BigInteger, comment="Timeout seconds")
    fallback: Mapped[int] = mapped_column(BigInteger, default=0, comment="Fallback flag")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, comment="Error message", nullable=True)
    input_snapshot: Mapped[dict] = mapped_column(JSON, comment="Input snapshot")
    result_json: Mapped[dict] = mapped_column(JSON, comment="Result json")
    raw_text: Mapped[Optional[str]] = mapped_column(Text, comment="Raw model output", nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/confirmed")
    reviewed_result_json: Mapped[Optional[dict]] = mapped_column(JSON, comment="Teacher reviewed result json", nullable=True)
    review_labels_json: Mapped[Optional[dict]] = mapped_column(JSON, comment="Structured teacher review labels", nullable=True)
    teacher_notes: Mapped[Optional[str]] = mapped_column(Text, comment="Teacher review notes", nullable=True)
    resolution_status: Mapped[Optional[str]] = mapped_column(String(30), comment="pending/in_progress/resolved/false_alarm", nullable=True)
    confirmed_by: Mapped[Optional[int]] = mapped_column(BigInteger, comment="Confirmed user id", nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="Confirmed time", nullable=True)
