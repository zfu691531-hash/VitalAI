# -*- coding: utf-8 -*-
"""
认证路由模块
============
- POST /api/auth/login: 用户登录，验证账号密码，返回JWT token与用户角色信息
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.user import LoginRequest, TokenResponse
from services.auth_service import create_token, verify_login

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    用户登录接口
    
    使用 JSON 格式提交：
    ```json
    {
        "username": "admin",
        "password": "admin123"
    }
    ```
    
    返回：
    - **access_token**: JWT访问令牌
    - **token_type**: 固定为 "bearer"
    """
    # 验证登录凭据
    user = verify_login(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成token
    access_token = create_token(user)
    
    # 返回标准格式
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
