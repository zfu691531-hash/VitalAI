# -*- coding: utf-8 -*-
"""
通用Schema
==========
- PaginationParams: 分页参数（page, page_size）
- BatchDeleteRequest: 批量删除请求（ids）
- IdRequest: 单个ID请求
"""

from pydantic import BaseModel
from typing import List


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 10


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[int]


class IdRequest(BaseModel):
    """单个ID请求"""
    id: int