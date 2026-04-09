# -*- coding: utf-8 -*-
"""
数据库连接与会话管理模块
========================
- 创建 SQLAlchemy 同步 Engine
- 提供 SessionLocal 工厂函数，用于创建数据库会话
- 提供 get_db 依赖注入函数，供路由层使用
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

# 引入 Base 以便后续 Base.metadata.create_all() 能感知到所有模型
from .base import Base  # noqa: F401

# 同步引擎，echo=False 关闭 SQL 日志（生产环境）
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True)

# Session 工厂
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
