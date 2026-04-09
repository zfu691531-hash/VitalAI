# -*- coding: utf-8 -*-
"""Rule RAG QA record model."""

from sqlalchemy import BigInteger, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class RuleQaRecord(Base, TimestampMixin):
    __tablename__ = "rule_qa_record"
    __table_args__ = (
        Index("idx_rule_qa_user_id", "user_id"),
        Index("idx_rule_qa_trace_id", "trace_id"),
        Index("idx_rule_qa_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="提问用户ID")
    question: Mapped[str] = mapped_column(Text, comment="用户问题")
    answer: Mapped[str] = mapped_column(Text, comment="系统回答")
    retrieved_chunks_json: Mapped[list | None] = mapped_column(JSON, comment="命中的知识片段")
    retrieval_meta_json: Mapped[dict | None] = mapped_column(JSON, comment="检索元信息")
    trace_id: Mapped[str] = mapped_column(String(64), comment="链路追踪ID")
    model_name: Mapped[str | None] = mapped_column(String(100), comment="回答模型名称")
    status: Mapped[str] = mapped_column(String(20), default="success", comment="success/failed")
