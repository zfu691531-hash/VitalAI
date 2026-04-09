# -*- coding: utf-8 -*-
"""
用户相关 Schema
===============
- LoginRequest: 登录请求（JSON格式）
- TokenResponse: 登录成功响应（access_token, token_type）
- PasswordChangeRequest: 修改密码请求
"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求（JSON格式）"""
    username: str = Field(..., description="登录账号")
    password: str = Field(..., description="登录密码")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    role: str
    name: str


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str = Field(..., description="固定为 bearer")


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    name: Optional[str] = Field(None, description="姓名")