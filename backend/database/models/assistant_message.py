# -*- coding: utf-8 -*-
"""Assistant conversation message model."""

from sqlalchemy import BigInteger, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class AssistantMessage(Base, TimestampMixin):
    __tablename__ = "assistant_message"
    __table_args__ = (
        Index("idx_assistant_message_session_id", "session_id"),
        Index("idx_assistant_message_role", "message_role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    session_id: Mapped[int] = mapped_column(BigInteger, comment="会话ID")
    user_id: Mapped[int] = mapped_column(BigInteger, comment="发送关联用户ID")
    message_role: Mapped[str] = mapped_column(String(20), comment="user/assistant/system")
    content: Mapped[str] = mapped_column(Text, comment="消息内容")
    meta_json: Mapped[dict | None] = mapped_column(JSON, comment="工具调用元信息")
