# -*- coding: utf-8 -*-
"""教师相关 Schema。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginationParams


class TeacherCreate(BaseModel):
    name: str = Field(..., description="姓名")
    subject: str = Field(..., description="学科")
    title: str = Field(..., description="职务")
    class_ids: Optional[str] = Field(None, description="班级ID列表，逗号分隔")


class TeacherUpdate(BaseModel):
    name: Optional[str] = Field(None, description="姓名")
    subject: Optional[str] = Field(None, description="学科")
    title: Optional[str] = Field(None, description="职务")
    class_ids: Optional[str] = Field(None, description="班级ID列表，逗号分隔")


class TeacherQuery(PaginationParams):
    keyword: Optional[str] = Field(None, description="关键词")
    subject: Optional[str] = Field(None, description="学科")


class TeacherBindClasses(BaseModel):
    teacher_id: int = Field(..., description="教师ID")
    class_ids: List[int] = Field(..., description="班级ID列表")


class TeacherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    title: str
    class_ids: Optional[str]
    class_names: Optional[str]
    created_at: datetime
    updated_at: datetime
