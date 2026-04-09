# -*- coding: utf-8 -*-
"""
用户路由模块（个人中心）
========================
- GET  /api/users/me: 获取当前登录用户个人信息
- PUT  /api/users/me: 修改个人信息（不含角色、账号）
- PUT  /api/users/me/password: 重置登录密码
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.response import success_response, error_response
from core.security import hash_password, verify_password
from database.connection import get_db
from database.models.user import User
from schemas.user import PasswordChangeRequest, UserUpdate, UserInfo

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me")
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前登录用户的个人信息
    
    返回：
    - id: 用户ID
    - username: 登录账号
    - role: 角色
    - name: 姓名
    """
    user_info = UserInfo(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        name=current_user.name
    )
    return success_response(data=user_info.model_dump(), msg="获取成功")


@router.put("/me")
def update_current_user_info(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改当前登录用户的个人信息
    
    请求体：
    - name: 姓名（可选）
    
    返回：
    - code: 状态码
    - msg: 提示信息
    """
    # 更新用户信息
    if user_update.name:
        current_user.name = user_update.name
    
    # 保存到数据库
    db.commit()
    db.refresh(current_user)
    
    return success_response(msg="个人信息更新成功")


@router.put("/me/password")
def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改当前登录用户的密码
    
    请求体：
    - old_password: 旧密码
    - new_password: 新密码
    
    返回：
    - code: 状态码
    - msg: 提示信息
    """
    # 验证旧密码
    if not verify_password(password_change.old_password, current_user.password_hash):
        return error_response(code=400, msg="旧密码错误")
    
    # 更新密码
    current_user.password_hash = hash_password(password_change.new_password)
    
    # 保存到数据库
    db.commit()
    
    return success_response(msg="密码修改成功")