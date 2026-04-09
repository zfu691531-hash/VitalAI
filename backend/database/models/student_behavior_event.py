# -*- coding: utf-8 -*-
"""Student behavior event model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentBehaviorEvent(Base, TimestampMixin):
    __tablename__ = "student_behavior_event"
    __table_args__ = (
        Index("idx_student_behavior_event_student_id", "student_id"),
        Index("idx_student_behavior_event_occurred_at", "occurred_at"),
        Index("idx_student_behavior_event_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    event_type: Mapped[str] = mapped_column(String(32), comment="Event type")
    event_level: Mapped[str] = mapped_column(String(20), comment="Event level")
    event_desc: Mapped[str] = mapped_column(Text, comment="Event description")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, comment="Occurred at")
