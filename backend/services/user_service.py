# -*- coding: utf-8 -*-
"""
用户服务模块（个人中心）
========================
- get_user_info: 查询当前用户个人信息
- update_user_info: 修改个人信息（排除角色、账号等不可修改字段）
- reset_password: 重置密码（需验证旧密码）
- get_student_by_user_id: 通过user.name匹配student.name获取学生记录
"""

from typing import Optional

from sqlalchemy.orm import Session

from database.models.user import User
from database.models.student import Student
from core.security import verify_password, hash_password
from core.response import success_response, error_response


def get_user_info(db: Session, user_id: int) -> dict:
    """
    查询当前用户个人信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
    
    Returns:
        dict: 用户信息
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return error_response(msg="用户不存在")
    
    return success_response(data={
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    })


def update_user_info(db: Session, user_id: int, name: Optional[str] = None) -> dict:
    """
    修改个人信息（排除角色、账号等不可修改字段）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        name: 姓名
    
    Returns:
        dict: 操作结果
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return error_response(msg="用户不存在")
    
    if name is not None:
        user.name = name
    
    db.commit()
    db.refresh(user)
    
    return success_response(msg="修改成功", data={
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
    })


def reset_password(db: Session, user_id: int, old_password: str, new_password: str) -> dict:
    """
    重置密码（需验证旧密码）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        old_password: 旧密码
        new_password: 新密码
    
    Returns:
        dict: 操作结果
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return error_response(msg="用户不存在")
    
    # 验证旧密码
    if not verify_password(old_password, user.password_hash):
        return error_response(msg="旧密码错误")
    
    # 更新密码
    user.password_hash = hash_password(new_password)
    db.commit()
    
    return success_response(msg="密码修改成功")


def get_student_by_user_id(db: Session, user_id: int) -> Optional[Student]:
    """
    通过user.name匹配student.name获取学生记录
    
    说明：student表没有user_id字段，只能通过姓名匹配关联
    
    Args:
        db: 数据库会话
        user_id: 用户ID
    
    Returns:
        Student: 学生对象，未找到返回None
    """
    # 1. 查询用户获取姓名
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # 2. 通过姓名匹配学生
    student = db.query(Student).filter(Student.name == user.name).first()
    return student
