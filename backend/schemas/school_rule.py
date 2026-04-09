# -*- coding: utf-8 -*-
"""校规相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginationParams


class SchoolRuleCreate(BaseModel):
    category: str = Field(..., description="分类")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")


class SchoolRuleUpdate(BaseModel):
    category: Optional[str] = Field(None, description="分类")
    title: Optional[str] = Field(None, description="标题")
    content: Optional[str] = Field(None, description="内容")


class SchoolRuleQuery(PaginationParams):
    category: Optional[str] = Field(None, description="分类")


class SchoolRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    title: str
    content: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
