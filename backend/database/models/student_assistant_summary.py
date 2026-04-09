# -*- coding: utf-8 -*-
"""Student assistant summary model."""

from typing import Optional

from sqlalchemy import BigInteger, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentAssistantSummary(Base, TimestampMixin):
    __tablename__ = "student_assistant_summary"
    __table_args__ = (Index("idx_student_assistant_summary_student_id", "student_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    summary_text: Mapped[str] = mapped_column(Text, comment="Summary text")
    signals_json: Mapped[Optional[dict]] = mapped_column(JSON, comment="Signals json", nullable=True)
