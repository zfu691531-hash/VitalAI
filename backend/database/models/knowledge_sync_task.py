# -*- coding: utf-8 -*-
"""Knowledge sync task model."""

from sqlalchemy import BigInteger, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class KnowledgeSyncTask(Base, TimestampMixin):
    __tablename__ = "knowledge_sync_task"
    __table_args__ = (
        Index("idx_kb_sync_status", "status"),
        Index("idx_kb_sync_rule_id", "rule_id"),
        Index("idx_kb_sync_task_type", "task_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    rule_id: Mapped[int | None] = mapped_column(BigInteger, comment="校规ID")
    task_type: Mapped[str] = mapped_column(String(30), comment="single/full")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/running/success/failed")
    payload_json: Mapped[dict | None] = mapped_column(JSON, comment="任务载荷")
    result_json: Mapped[dict | None] = mapped_column(JSON, comment="任务结果")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
