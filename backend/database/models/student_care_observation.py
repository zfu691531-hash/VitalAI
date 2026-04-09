# -*- coding: utf-8 -*-
"""Student care observation model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareObservation(Base, TimestampMixin):
    __tablename__ = "student_care_observation"
    __table_args__ = (
        Index("idx_student_care_observation_student_id", "student_id"),
        Index("idx_student_care_observation_dimension", "dimension"),
        Index("idx_student_care_observation_observed_at", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    dimension: Mapped[str] = mapped_column(String(20), comment="emotion/social/safety/family/study/behavior")
    observation_type: Mapped[str] = mapped_column(String(40), comment="Observation type")
    observation_level: Mapped[str] = mapped_column(String(20), comment="low/medium/high")
    observed_at: Mapped[datetime] = mapped_column(DateTime, comment="Observed at")
    summary: Mapped[str] = mapped_column(Text, comment="Observation summary")
