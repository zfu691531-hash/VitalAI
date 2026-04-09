# -*- coding: utf-8 -*-
"""
统一响应格式模块
================
所有接口返回统一的 { code, msg, data } 格式：
- code: 状态码（200=成功，非200=失败）
- msg:  提示信息
- data: 返回数据（可选）
提供 success_response / error_response 快捷方法。
"""

from typing import Any

from pydantic import BaseModel


class ResponseModel(BaseModel):
    """统一响应模型，所有接口返回此结构。"""

    code: int = 200
    msg: str = "success"
    data: Any = None


def success_response(data: Any = None, msg: str = "操作成功") -> dict:
    """构造成功响应。"""
    return {"code": 200, "msg": msg, "data": data}


def error_response(code: int = 400, msg: str = "操作失败", data: Any = None) -> dict:
    """构造失败响应。"""
    return {"code": code, "msg": msg, "data": data}
