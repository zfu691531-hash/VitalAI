# -*- coding: utf-8 -*-
"""
用户表模型（user）
==================
存储所有用户的登录信息与基础身份信息。
字段：id(主键), username(账号,唯一), password_hash(加密密码), role(角色:student/teacher/admin),
      name(姓名), created_at, updated_at
"""

from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """用户表，存储登录账号与身份信息。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键",
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, comment="登录账号，唯一",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), comment="密码哈希(bcrypt, 60字符)",
    )
    role: Mapped[str] = mapped_column(
        Enum("student", "teacher", "admin"),
        comment="角色: student-学生, teacher-教师, admin-校务管理员",
    )
    name: Mapped[str] = mapped_column(
        String(50), comment="真实姓名",
    )
