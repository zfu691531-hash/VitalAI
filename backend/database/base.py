# -*- coding: utf-8 -*-
"""
声明式基类模块
==============
定义 SQLAlchemy DeclarativeBase，所有 ORM 模型继承此基类。
提供公共字段：id（主键）、created_at、updated_at。
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


class TimestampMixin:
    """时间戳混入，为模型提供 created_at 和 updated_at 字段。"""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
