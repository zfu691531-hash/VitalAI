from __future__ import annotations

# -*- coding: utf-8 -*-
"""Student tag definition model."""

from typing import Optional

from sqlalchemy import BigInteger, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentTagDefinition(Base, TimestampMixin):
    __tablename__ = "student_tag_definition"
    __table_args__ = (
        Index("idx_student_tag_definition_scope", "scope_type", "scope_value"),
        Index("idx_student_tag_definition_tag", "tag_text"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    scope_type: Mapped[str] = mapped_column(String(20), comment="school/grade/class")
    scope_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="scope value")
    tag_text: Mapped[str] = mapped_column(String(50), comment="Tag text")
    polarity: Mapped[str] = mapped_column(String(20), comment="positive/neutral/negative")
    dimension: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="dimension")
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="custom weight")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="description")
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="created by user id")
