# -*- coding: utf-8 -*-
"""School rule chunk mirror model."""

from sqlalchemy import BigInteger, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class SchoolRuleChunk(Base, TimestampMixin):
    __tablename__ = "school_rule_chunk"
    __table_args__ = (
        Index("idx_rule_chunk_rule_id", "rule_id"),
        Index("idx_rule_chunk_status", "status"),
        Index("idx_rule_chunk_milvus_pk", "milvus_pk"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    rule_id: Mapped[int] = mapped_column(BigInteger, comment="校规ID")
    rule_version: Mapped[int] = mapped_column(BigInteger, default=1, comment="校规版本")
    chunk_index: Mapped[int] = mapped_column(BigInteger, comment="切片序号")
    chunk_text: Mapped[str] = mapped_column(Text, comment="切片文本")
    keywords_json: Mapped[list | None] = mapped_column(JSON, comment="关键词")
    sparse_vector_meta_json: Mapped[dict | None] = mapped_column(JSON, comment="稀疏向量元信息")
    dense_model_name: Mapped[str | None] = mapped_column(String(100), comment="稠密向量模型名称")
    sparse_model_name: Mapped[str | None] = mapped_column(String(100), comment="稀疏向量模型名称")
    milvus_collection: Mapped[str | None] = mapped_column(String(100), comment="Milvus集合名")
    milvus_pk: Mapped[str | None] = mapped_column(String(100), comment="Milvus主键")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/synced/failed")
