# -*- coding: utf-8 -*-
"""班级相关 Schema。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginationParams


class ClassCreate(BaseModel):
    grade: str = Field(..., description="年级")
    name: str = Field(..., description="班级名称")
    head_teacher_id: int = Field(..., description="班主任ID")
    max_count: int = Field(..., description="最大人数")
    status: int = Field(1, description="状态：1-在读，0-毕业")


class ClassUpdate(BaseModel):
    grade: Optional[str] = Field(None, description="年级")
    name: Optional[str] = Field(None, description="班级名称")
    head_teacher_id: Optional[int] = Field(None, description="班主任ID")
    max_count: Optional[int] = Field(None, description="最大人数")
    status: Optional[int] = Field(None, description="状态：1-在读，0-毕业")


class ClassQuery(PaginationParams):
    grade: Optional[str] = Field(None, description="年级")
    status: Optional[int] = Field(1, description="状态：1-在读，0-毕业")


class ClassStudentBind(BaseModel):
    class_id: int = Field(..., description="班级ID")
    student_ids: List[int] = Field(..., description="学生ID列表")


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grade: str
    name: str
    head_teacher_id: int
    head_teacher_name: str
    max_count: int
    current_count: int
    status: int
    created_at: datetime
    updated_at: datetime
