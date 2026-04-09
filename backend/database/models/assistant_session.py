# -*- coding: utf-8 -*-
"""Assistant conversation session model."""

from sqlalchemy import BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class AssistantSession(Base, TimestampMixin):
    __tablename__ = "assistant_session"
    __table_args__ = (
        Index("idx_assistant_session_user_id", "user_id"),
        Index("idx_assistant_session_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="用户ID")
    role_snapshot: Mapped[str] = mapped_column(String(20), comment="会话创建时的角色快照")
    title: Mapped[str | None] = mapped_column(String(100), comment="会话标题")
    status: Mapped[str] = mapped_column(String(20), default="active", comment="active/archived")
