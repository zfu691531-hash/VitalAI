# -*- coding: utf-8 -*-
"""
认证服务模块
============
- verify_login: 验证账号密码合法性，返回用户信息（自动查询角色）
- create_token: 生成JWT token（包含user_id、role）
"""

from typing import Optional

from sqlalchemy.orm import Session

from core.security import verify_password, create_access_token
from database.models.user import User


def verify_login(db: Session, username: str, password: str) -> Optional[User]:
    """
    验证账号密码合法性，返回用户信息。
    
    说明：不通过参数传递role，而是从数据库查询用户后自动获取角色，
    避免安全风险（用户伪造角色）。
    
    Args:
        db: 数据库会话
        username: 用户名
        password: 密码
    
    Returns:
        User: 验证成功返回用户对象，失败返回None
    """
    # 根据用户名查询用户
    user = db.query(User).filter(User.username == username).first()
    
    # 验证用户是否存在且密码正确
    if user and verify_password(password, user.password_hash):
        return user
    return None


def create_token(user: User) -> str:
    """生成JWT token，包含user_id、role。"""
    return create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role
        }
    )
