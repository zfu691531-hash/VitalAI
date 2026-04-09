# -*- coding: utf-8 -*-
"""Rule RAG feedback model."""

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class RuleQaFeedback(Base, TimestampMixin):
    __tablename__ = "rule_qa_feedback"
    __table_args__ = (
        Index("idx_rule_feedback_status", "status"),
        Index("idx_rule_feedback_qa_record_id", "qa_record_id"),
        Index("idx_rule_feedback_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    qa_record_id: Mapped[int] = mapped_column(BigInteger, comment="问答记录ID")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="反馈用户ID")
    rating: Mapped[str] = mapped_column(String(20), comment="up/down")
    improvement_reason: Mapped[str | None] = mapped_column(Text, comment="改进理由")
    suggested_answer: Mapped[str | None] = mapped_column(Text, comment="建议答案")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/adopted/revised/rejected")
    review_note: Mapped[str | None] = mapped_column(Text, comment="管理员处理说明")
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, comment="处理管理员ID")
