# -*- coding: utf-8 -*-
"""Student family contact summary model."""

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentFamilyContact(Base, TimestampMixin):
    __tablename__ = "student_family_contact"
    __table_args__ = (Index("idx_student_family_contact_student_id", "student_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    student_id: Mapped[int] = mapped_column(BigInteger, comment="Student id")
    contact_type: Mapped[str] = mapped_column(String(20), comment="Contact type")
    summary: Mapped[str] = mapped_column(Text, comment="Contact summary")
