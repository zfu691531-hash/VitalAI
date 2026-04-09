# -*- coding: utf-8 -*-
"""正式分班批次模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class PlacementBatch(Base, TimestampMixin):
    __tablename__ = "placement_batch"
    __table_args__ = (
        Index("idx_placement_batch_grade", "grade"),
        Index("idx_placement_batch_created_by", "created_by"),
        Index("idx_placement_batch_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    grade: Mapped[str] = mapped_column(String(20), comment="年级")
    batch_name: Mapped[str] = mapped_column(String(100), comment="批次名称")
    created_by: Mapped[int] = mapped_column(BigInteger, comment="创建人用户 ID")
    student_count: Mapped[int] = mapped_column(Integer, comment="学生总数")
    class_count: Mapped[int] = mapped_column(Integer, comment="班级总数")
    status: Mapped[str] = mapped_column(String(20), comment="draft 或 confirmed")
    balance_factors: Mapped[list] = mapped_column(JSON, comment="均衡因素")
    assignment_result_json: Mapped[list] = mapped_column(JSON, comment="分班结果 JSON")
    summary_json: Mapped[dict] = mapped_column(JSON, comment="统计摘要 JSON")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="确认时间")
