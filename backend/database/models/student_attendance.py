from __future__ import annotations

# -*- coding: utf-8 -*-
"""Student attendance record model."""

from datetime import date
from typing import Optional

from sqlalchemy import BigInteger, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentAttendance(Base, TimestampMixin):
    __tablename__ = "student_attendance"
    __table_args__ = (
        Index("idx_student_attendance_student_id", "student_id"),
        Index("idx_student_attendance_date", "date"),
        Index("idx_student_attendance_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    date: Mapped[date] = mapped_column(Date, comment="Attendance date")
    status: Mapped[str] = mapped_column(String(20), comment="Attendance status")
    remark: Mapped[Optional[str]] = mapped_column(String(255), comment="Remark", nullable=True)
