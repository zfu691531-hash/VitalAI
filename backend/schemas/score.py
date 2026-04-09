# -*- coding: utf-8 -*-
"""成绩相关 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import PaginationParams


class ScoreCreate(BaseModel):
    student_id: int = Field(..., description="学生ID")
    class_id: int = Field(..., description="班级ID")
    exam_batch: str = Field(..., description="考试批次")
    subject: str = Field(..., description="科目")
    score: float = Field(..., description="分数")

    @field_validator("score")
    @classmethod
    def validate_score(cls, value):
        if not 0 <= value <= 100:
            raise ValueError("分数必须在 0-100 之间")
        return value


class ScoreUpdate(BaseModel):
    student_id: Optional[int] = Field(None, description="学生ID")
    class_id: Optional[int] = Field(None, description="班级ID")
    exam_batch: Optional[str] = Field(None, description="考试批次")
    subject: Optional[str] = Field(None, description="科目")
    score: Optional[float] = Field(None, description="分数")

    @field_validator("score")
    @classmethod
    def validate_score(cls, value):
        if value is not None and not 0 <= value <= 100:
            raise ValueError("分数必须在 0-100 之间")
        return value


class ScoreQuery(PaginationParams):
    student_id: Optional[int] = Field(None, description="学生ID")
    class_id: Optional[int] = Field(None, description="班级ID")
    exam_batch: Optional[str] = Field(None, description="考试批次")
    subject: Optional[str] = Field(None, description="科目")


class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    exam_batch: str
    subject: str
    score: float
    created_at: datetime
    updated_at: datetime


class ScoreStatsResponse(BaseModel):
    subject: str
    average: float
    maximum: float
    minimum: float
    count: int
