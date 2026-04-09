# -*- coding: utf-8 -*-
"""Bayesian override rules for student care."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class StudentCareBayesRule(Base, TimestampMixin):
    __tablename__ = "student_care_bayes_rule"
    __table_args__ = (
        Index("idx_student_care_bayes_dimension", "dimension"),
        Index("idx_student_care_bayes_rule_key", "dimension", "evidence_key", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Primary key")
    dimension: Mapped[str] = mapped_column(String(20), comment="emotion/family/safety")
    evidence_key: Mapped[str] = mapped_column(String(80), comment="__base__ or evidence key")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="enabled")
    prior: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="prior probability")
    blend_alpha: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="blend alpha")
    likelihood_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="likelihood ratio")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="description")
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="updated by user id")
