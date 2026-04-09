# -*- coding: utf-8 -*-
"""教师分组方案模型。"""

from sqlalchemy import BigInteger, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class GroupScheme(Base, TimestampMixin):
    __tablename__ = "group_scheme"
    __table_args__ = (
        Index("idx_group_scheme_class_id", "class_id"),
        Index("idx_group_scheme_created_by", "created_by"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(BigInteger, comment="班级 ID")
    created_by: Mapped[int] = mapped_column(BigInteger, comment="创建人用户 ID")
    scheme_name: Mapped[str] = mapped_column(String(100), comment="方案名称")
    group_count: Mapped[int] = mapped_column(Integer, comment="分组数量")
    balance_factors: Mapped[list] = mapped_column(JSON, comment="均衡因素")
    group_result_json: Mapped[list] = mapped_column(JSON, comment="分组结果 JSON")
    source_type: Mapped[str] = mapped_column(String(20), comment="manual 或 ai")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注或说明")
